# Audio

Baseline dialog system:
- speaker profiles in `assets/audio/voices/<speaker>/profile.yaml`
- uses prerecorded line wavs when available
- otherwise generates lightweight offline synthetic voice tones

Music baseline:
- selects track from `music_library/catalog.yaml` by tag overlap with scene vibe
- if source track missing, synthesizes a fallback bed

Mixing:
- ffmpeg sidechain ducking + loudnorm when available
- NumPy fallback mix if ffmpeg is unavailable
- outputs `final_audio.wav` and optional `subtitles.srt`
