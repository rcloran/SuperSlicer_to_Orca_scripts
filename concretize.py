#!/usr/bin/env python3

import argparse
import json
import os
import sys


def filename_for_profile(base_dir, t, profile):
    tmap = {
        "machine": "printer_",
        "filament": "filament_",
        "process": "",
    }
    if profile == "*common*":
        profile = f"{tmap[t]}*common*"
    return os.path.join(base_dir, profile + ".json")


def concretize(filename, ignored, allowed):
    base_dir = os.path.dirname(filename)
    d = json.load(open(filename))
    inherited = list(filter(lambda x: x, d.get("inherits", "").split("; ")))
    r = {}

    new_inherits = []
    for i in inherited:
        if i in ignored:
            continue
        if i in allowed:
            new_inherits.append(i)
            continue
        t = d.get("type", os.path.basename(base_dir))
        data = concretize(filename_for_profile(base_dir, t, i), ignored, allowed)
        assert not ("inherits" in r and "inherits" in data)
        r.update(data.items())

    new_inherits = new_inherits + list(filter(None, [r.pop("inherits", None)]))
    assert len(new_inherits) <= 1
    d.pop("inherits", None)
    r.update(d.items())
    if new_inherits:
        r["inherits"] = new_inherits[0]
    return r


def main(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument("--ignore", default=[], action="append")
    parser.add_argument("--allow", default=[], action="append")

    args = parser.parse_args(argv)

    d = concretize(args.filename, args.ignore, args.allow)
    print(json.dumps(d, indent=4, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
