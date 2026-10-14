"""Test step: exercises the protocol. params: sleep (s), fail (code), oom (bool), licenses (list)."""

import json
import os
import time

from steps._common import StepError, main, progress


class OutOfMemoryError(RuntimeError):  # stands in for torch.cuda.OutOfMemoryError
    pass


def run(op, in_dir, out_dir, params):
    print("library noise")  # must land on stderr, not in the protocol
    os.write(1, b"C-level noise\n")
    progress(0.5, f"op={op}")
    time.sleep(params.get("sleep", 0))
    if params.get("oom"):
        raise OutOfMemoryError("CUDA out of memory (fake)")
    if params.get("fail"):
        raise StepError(params["fail"], "asked to fail")
    if "exit" in params:  # a native crash: the process ends without a word
        os._exit(params["exit"])
    with open(os.path.join(out_dir, "echo.json"), "w") as f:
        json.dump({"op": op, "in": in_dir, "params": params}, f)
    return {
        "outputs": {"echo": "echo.json"},
        "metrics": {"op": op},
        "licenses": params.get("licenses", []),
    }


if __name__ == "__main__":
    main(run)
