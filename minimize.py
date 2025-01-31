#!/usr/bin/env python3

import argparse
import json
import os
import sys

import concretize


def filename_for_profile(superclass, child_filename):
    return os.path.join(os.path.dirname(child_filename), superclass + ".json")


ALWAYS = ["from", "inherits", "instantiation", "type", "printer_model", "nozzle_diameter"]


def minimize(filename):
    d = json.load(open(filename))
    inherits = d.get("inherits", None)
    if not inherits:
        return d

    inherited = concretize.concretize(filename_for_profile(inherits, filename), [], [])

    r = {}
    for k, v in d.items():
        i = inherited.get(k, None)
        if k in ALWAYS or not (i == v or i == [v]):
            r[k] = v

    return r


def main(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("filename")
    args = parser.parse_args(argv)

    d = minimize(args.filename)
    print(json.dumps(d, indent=4, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
