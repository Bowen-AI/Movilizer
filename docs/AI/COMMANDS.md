# Command Spec (Machine-Readable)

```yaml
commands:
  - name: run
    module: studio.run
    usage: "python -m studio.run --workspace <path> [--projects all|<p...>] [--scenes all|<s...>]"
    flags:
      - {name: --workspace, type: str, required: true}
      - {name: --projects, type: list[str], required: false}
      - {name: --project, type: str, required: false}
      - {name: --scenes, type: list[str], required: false}
      - {name: --scene, type: str, required: false}
      - {name: --shots, type: list[str], required: false}
      - {name: --shot, type: str, required: false}
      - {name: --patch, type: list[path], required: false}
      - {name: --dry_run, type: bool, required: false}
      - {name: --resume, type: bool, required: false}
      - {name: --compile_only, type: bool, required: false}
      - {name: --skip_eval, type: bool, required: false}
      - {name: --run_id, type: str, required: false}

  - name: train_identity
    module: studio.train_identity
    usage: "python -m studio.train_identity --config configs/train/sdxl_lora.yaml"
    flags:
      - {name: --config, type: path, required: true}

  - name: eval
    module: studio.eval
    usage: "python -m studio.eval --workspace workspace.yaml --run_id <id>"
    flags:
      - {name: --workspace, type: path, required: true}
      - {name: --run_id, type: str, required: true}

  - name: evolve
    module: studio.evolve
    usage: "python -m studio.evolve --workspace workspace.yaml --projects <p...> --budget small"
    flags:
      - {name: --workspace, type: path, required: true}
      - {name: --projects, type: list[str], required: false}
      - {name: --budget, type: enum[small,medium,large], required: false}
      - {name: --config, type: path, required: false}
      - {name: --mode, type: enum[weighted_sum,pareto], required: false}
      - {name: --resume, type: bool, required: false}
      - {name: --run_id, type: str, required: false}

  - name: tweak
    module: studio.tweak
    usage: "python -m studio.tweak --workspace workspace.yaml --project <p> --scene <s> --create_patch_template"
    flags:
      - {name: --workspace, type: path, required: false}
      - {name: --project, type: str, required: true}
      - {name: --scene, type: str, required: true}
      - {name: --shot, type: str, required: false}
      - {name: --create_patch_template, type: bool, required: false}
      - {name: --apply_inline, type: str, required: false}

  - name: ai
    module: studio.ai
    usage: "python -m studio.ai [--interactive] [--workspace workspace.yaml] \"<request>\""
    flags:
      - {name: request, type: str, required: conditional}
      - {name: --interactive, type: bool, required: false}
      - {name: --workspace, type: path, required: false}
      - {name: --project, type: str, required: false}
      - {name: --scene, type: str, required: false}
      - {name: --shot, type: str, required: false}
      - {name: --backend, type: enum[rules,llm], required: false}
      - {name: --dry_run, type: bool, required: false}
      - {name: --yes, type: bool, required: false}
      - {name: --run_id, type: str, required: false}
      - {name: --config, type: path, required: false}

  - name: tools.extract_frames
    module: studio.tools.extract_frames
    usage: "python -m studio.tools.extract_frames --input in.mp4 --output out_frames"

  - name: tools.auto_caption
    module: studio.tools.auto_caption
    usage: "python -m studio.tools.auto_caption --images data/id/train/images --captions data/id/train/captions"

  - name: tools.face_crop_align
    module: studio.tools.face_crop_align
    usage: "python -m studio.tools.face_crop_align --input data/id/train/images --output data/id/train/aligned"

  - name: tools.dataset_report
    module: studio.tools.dataset_report
    usage: "python -m studio.tools.dataset_report --dataset_root data/my_identity"
```
