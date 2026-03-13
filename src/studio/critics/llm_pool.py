"""LLM pool for managing multiple local open-weight model instances."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LLMPool:
    """Manages local open-weight LLM instances with fallback support."""

    def __init__(self, use_mock: bool = False, mock_mode: bool = False):
        """Initialize LLM pool.

        Args:
            use_mock: Force mock mode for testing
            mock_mode: Enable mock mode automatically if imports fail
        """
        self.use_mock = use_mock
        self.mock_mode = use_mock or mock_mode
        self.models = {}
        self.available_backends = []

        if not self.use_mock:
            self._detect_available_backends()

    def _detect_available_backends(self) -> None:
        """Detect which backends are available."""
        try:
            import vllm  # noqa: F401

            self.available_backends.append("vllm")
            logger.info("vLLM backend detected")
        except ImportError:
            logger.debug("vLLM not available")

        try:
            import transformers  # noqa: F401

            self.available_backends.append("transformers")
            logger.info("Transformers backend detected")
        except ImportError:
            logger.debug("Transformers not available")

        if not self.available_backends:
            logger.warning(
                "No LLM backends available; falling back to mock mode"
            )
            self.mock_mode = True

    async def load_model(
        self,
        model_id: str,
        backend: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Load a model into the pool.

        Args:
            model_id: HuggingFace model identifier
            backend: Preferred backend ('vllm', 'transformers', or auto)
            **kwargs: Backend-specific parameters (gpu_memory_utilization, etc.)

        Returns:
            True if loaded successfully, False otherwise
        """
        if model_id in self.models:
            logger.info(f"Model {model_id} already loaded")
            return True

        if self.mock_mode:
            logger.info(f"Mock mode: registering model {model_id}")
            self.models[model_id] = {"backend": "mock", "config": kwargs}
            return True

        # Try specified backend first
        backends_to_try = []
        if backend:
            backends_to_try.append(backend)
        backends_to_try.extend(self.available_backends)

        for backend_name in backends_to_try:
            try:
                if backend_name == "vllm":
                    return await self._load_vllm(model_id, **kwargs)
                elif backend_name == "transformers":
                    return await self._load_transformers(model_id, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Failed to load {model_id} with {backend_name}: {e}"
                )
                continue

        logger.warning(f"Failed to load {model_id}, falling back to mock")
        self.models[model_id] = {"backend": "mock", "config": kwargs}
        return False

    async def _load_vllm(self, model_id: str, **kwargs: Any) -> bool:
        """Load model with vLLM."""
        try:
            from vllm import AsyncLLMEngine, EngineArgs

            logger.info(f"Loading {model_id} with vLLM")

            # Default vLLM args
            engine_args = EngineArgs(
                model=model_id,
                dtype="auto",
                gpu_memory_utilization=kwargs.get("gpu_memory_utilization", 0.8),
                tensor_parallel_size=kwargs.get("tensor_parallel_size", 1),
                max_model_len=kwargs.get("max_model_len", None),
            )

            engine = AsyncLLMEngine.from_engine_args(engine_args)
            self.models[model_id] = {
                "backend": "vllm",
                "engine": engine,
                "config": kwargs,
            }
            logger.info(f"Successfully loaded {model_id} with vLLM")
            return True
        except Exception as e:
            logger.error(f"vLLM loading failed: {e}")
            raise

    async def _load_transformers(self, model_id: str, **kwargs: Any) -> bool:
        """Load model with transformers."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info(f"Loading {model_id} with transformers")

            device = kwargs.get("device", "cuda")
            dtype = kwargs.get("dtype", "auto")

            tokenizer = AutoTokenizer.from_pretrained(
                model_id, trust_remote_code=True
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map=device,
                torch_dtype=dtype,
                trust_remote_code=True,
            )

            self.models[model_id] = {
                "backend": "transformers",
                "model": model,
                "tokenizer": tokenizer,
                "config": kwargs,
            }
            logger.info(f"Successfully loaded {model_id} with transformers")
            return True
        except Exception as e:
            logger.error(f"Transformers loading failed: {e}")
            raise

    async def generate(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.95,
        **kwargs: Any,
    ) -> str:
        """Generate text from a model.

        Args:
            model_id: Model to use
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        if model_id not in self.models:
            logger.warning(
                f"Model {model_id} not loaded, attempting to load"
            )
            await self.load_model(model_id)

        model_info = self.models.get(model_id)
        if not model_info:
            logger.error(f"Model {model_id} not available")
            return self._mock_response()

        backend = model_info["backend"]

        try:
            if backend == "vllm":
                return await self._generate_vllm(
                    model_id, prompt, max_tokens, temperature, top_p, **kwargs
                )
            elif backend == "transformers":
                return await self._generate_transformers(
                    model_id, prompt, max_tokens, temperature, top_p, **kwargs
                )
            else:  # mock
                return self._mock_response()
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return self._mock_response()

    async def _generate_vllm(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        **kwargs: Any,
    ) -> str:
        """Generate with vLLM backend."""
        from vllm import SamplingParams

        engine = self.models[model_id]["engine"]

        sampling_params = SamplingParams(
            n=1,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            **kwargs,
        )

        results = await engine.generate(
            prompt, sampling_params, request_id=None
        )

        if results:
            return results[0].outputs[0].text
        return self._mock_response()

    async def _generate_transformers(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        **kwargs: Any,
    ) -> str:
        """Generate with transformers backend."""
        model_info = self.models[model_id]
        tokenizer = model_info["tokenizer"]
        model = model_info["model"]

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def _generate():
            inputs = tokenizer.encode(prompt, return_tensors="pt")
            with model.device:
                outputs = model.generate(
                    inputs,
                    max_length=len(inputs[0]) + max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    **kwargs,
                )
            return tokenizer.decode(outputs[0], skip_special_tokens=True)

        result = await loop.run_in_executor(None, _generate)
        return result

    def _mock_response(self, response_type: str = "generic") -> str:
        """Generate mock response for testing.

        Args:
            response_type: Type of response ('generic', 'json', 'structured')

        Returns:
            Mock response string
        """
        if response_type == "json":
            return json.dumps(
                {
                    "score": 8.0,
                    "issues": [],
                    "suggestions": ["Consider improving visuals"],
                }
            )
        elif response_type == "structured":
            return """
Score: 8.0
Issues: None
Suggestions:
- Consider improving visuals
- Enhance color grading

Reasoning: This is a mock response for testing.
"""
        else:
            return "Mock LLM response for testing purposes."

    async def unload_model(self, model_id: str) -> None:
        """Unload a model to free resources."""
        if model_id in self.models:
            model_info = self.models[model_id]
            backend = model_info["backend"]

            try:
                if backend == "vllm":
                    engine = model_info.get("engine")
                    if engine:
                        await engine.shutdown()
                elif backend == "transformers":
                    model = model_info.get("model")
                    if model:
                        del model
                        del model_info["tokenizer"]
            except Exception as e:
                logger.warning(f"Error unloading {model_id}: {e}")

            del self.models[model_id]
            logger.info(f"Unloaded model {model_id}")

    async def shutdown(self) -> None:
        """Shutdown all models."""
        for model_id in list(self.models.keys()):
            await self.unload_model(model_id)
        logger.info("LLM pool shutdown complete")
