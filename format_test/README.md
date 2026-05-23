# Format Test Results

This directory contains local format conversion tests for:

- JPG
- PNG
- WEBP
- SVG
- PDF

## Important

`run_format_tests.ps1` sets `GENERATOR_MODE=placeholder` so the test finishes
quickly. It verifies:

- file upload
- input normalization to PNG
- job state handling
- OBJ export
- 3MF export
- GLB preview export
- download endpoints

It does not run TripoSR for every format. Running TripoSR for all five formats
can take a long time and may appear stalled because the model logs are produced
inside child processes.

## Results

See:

```text
format_test/results/summary.json
```

Each format has its own directory:

```text
format_test/results/jpg
format_test/results/png
format_test/results/webp
format_test/results/svg
format_test/results/pdf
```

Each successful result directory contains:

- original sample input
- `input.png`
- `output.obj`
- `output.3mf`
- `preview.glb`
- `downloaded_model.zip`
- `downloaded_output.3mf`
- `status.json`

