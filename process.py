#!/usr/bin/env python3

import argparse
import re
import json
import os
import shutil
import sys

import concretize
import minimize

TARGETS = {
    "machine": [
        "Original Prusa MK4S 0.*",
        "Original Prusa MK4S HF.*",
        "Original Prusa MK4 Input Shaper 0.4 nozzle.json",
    ],
    "process": [
        "0.* (DETAIL|DRAFT|QUALITY|SPEED|STRUCTURAL) @MK4S 0.*",
        "0.* @MK4S HF0.*",
        r"\*MK4IS_common\*.*",
    ],
    "filament": [
        "Generic (ABS|ASA|FLEX|PETG|PLA|PLA Silk) @MK4S.*",
        "Prusament ASA @MK4S.*",
    ],
}

RENAME = {
    "machine": [
        ("Original Prusa MK4S (.*)", r"Prusa MK4S \1"),
        (
            "Original Prusa MK4 Input Shaper 0.4 nozzle.json",
            "fdm_machine_common_mk4s.json",
        ),
    ],
    "filament": [
        ("Prusament ASA (.*)", r"Prusa Generic ASA \1"),
        ("Generic FLEX (.*)", r"Prusa Generic TPU \1"),
        ("Generic (.*)", r"Prusa Generic \1"),
    ],
    "process": [(r"\*MK4IS_common\*.json", "process_common_mk4s.json")],
}

INHERITANCE = {
    "machine": [
        ("fdm_machine_common_mk4s.json", "fdm_machine_common"),
        ("Prusa MK4S 0.4 nozzle.json", "fdm_machine_common_mk4s"),
        ("Prusa MK4S 0..*", "Prusa MK4S 0.4 nozzle"),
        ("Prusa MK4S HF0.4 nozzle.json", "Prusa MK4S 0.4 nozzle"),
        ("Prusa MK4S HF.*", "Prusa MK4S HF0.4 nozzle"),
    ],
    "process": [
        ("process_common_mk4s.json", "fdm_process_common"),
        ("0.05mm DETAIL @MK4S 0.25.json", "0.07mm DETAIL @MK4S 0.25"),
        ("0.10mm FAST DETAIL @MK4S 0.4.json", "0.15mm SPEED @MK4S 0.4"),
        ("0.12mm STRUCTURAL @MK4S 0.25.json", "0.12mm SPEED @MK4S 0.25"),
        ("0.15mm SPEED @MK4S 0.25.json", "0.12mm SPEED @MK4S 0.25"),
        ("0.15mm SPEED @MK4S HF0.4.json", "0.15mm SPEED @MK4S 0.4"),
        ("0.15mm STRUCTURAL @MK4S 0.25.json", "0.15mm SPEED @MK4S 0.25"),
        ("0.15mm STRUCTURAL @MK4S 0.4.json", "0.20mm STRUCTURAL @MK4S 0.4"),
        ("0.16mm SPEED @MK4S 0.3.json", "0.16mm STRUCTURAL @MK4S 0.3"),
        ("0.16mm STRUCTURAL @MK4S 0.3.json", "0.12mm STRUCTURAL @MK4S 0.3"),
        ("0.20mm SPEED @MK4S 0.3.json", "0.16mm SPEED @MK4S 0.3"),
        ("0.20mm SPEED @MK4S HF0.5.json", "0.20mm SPEED @MK4S 0.5"),
        ("0.20mm SPEED @MK4S HF0.6.json", "0.20mm SPEED @MK4S 0.6"),
        ("0.20mm STRUCTURAL @MK4S 0.3.json", "0.16mm STRUCTURAL @MK4S 0.3"),
        ("0.20mm STRUCTURAL @MK4S 0.5.json", "0.20mm SPEED @MK4S 0.5"),
        ("0.20mm STRUCTURAL @MK4S 0.6.json", "0.20mm SPEED @MK4S 0.6"),
        ("0.25mm SPEED @MK4S 0.5.json", "0.20mm SPEED @MK4S 0.5"),
        ("0.25mm SPEED @MK4S HF0.5.json", "0.25mm SPEED @MK4S 0.5"),
        ("0.25mm SPEED @MK4S HF0.6.json", "0.25mm SPEED @MK4S 0.6"),
        ("0.25mm STRUCTURAL @MK4S 0.5.json", "0.20mm STRUCTURAL @MK4S 0.5"),
        ("0.25mm STRUCTURAL @MK4S 0.6.json", "0.25mm SPEED @MK4S 0.6"),
        ("0.25mm STRUCTURAL @MK4S HF0.4.json", "0.20mm STRUCTURAL @MK4S 0.4"),
        ("0.30mm SPEED @MK4S HF0.8.json", "0.30mm DETAIL @MK4S 0.8"),
        ("0.30mm STRUCTURAL @MK4S HF0.8.json", "0.30mm DETAIL @MK4S 0.8"),
        ("0.32mm SPEED @MK4S HF0.5.json", "0.25mm SPEED @MK4S HF0.5"),
        ("0.32mm SPEED @MK4S HF0.6.json", "0.32mm SPEED @MK4S 0.6"),
        ("0.32mm STRUCTURAL @MK4S 0.6.json", "0.32mm SPEED @MK4S 0.6"),
        ("0.32mm STRUCTURAL @MK4S HF0.5.json", "0.25mm STRUCTURAL @MK4S 0.5"),
        ("0.32mm STRUCTURAL @MK4S HF0.6.json", "0.32mm SPEED @MK4S 0.6"),
        ("0.40mm SPEED @MK4S HF0.8.json", "0.40mm QUALITY @MK4S 0.8"),
        ("0.40mm STRUCTURAL @MK4S HF0.6.json", "0.40mm SPEED @MK4S HF0.6"),
        ("0.40mm STRUCTURAL @MK4S HF0.8.json", "0.40mm QUALITY @MK4S 0.8"),
        ("0.55mm SPEED @MK4S HF0.8.json", "0.55mm DRAFT @MK4S 0.8"),
        ("0.55mm STRUCTURAL @MK4S HF0.8.json", "0.55mm DRAFT @MK4S 0.8"),
        (".*", "process_common_mk4s"),
    ],
    "filament": [
        (".*ABS @MK4S 0.*", "Prusa Generic ABS @MK4S"),
        (".*ABS @MK4S HF0.4.*", "Prusa Generic ABS @MK4S"),
        (".*ABS @MK4S HF0..*", "Prusa Generic ABS @MK4S HF0.4"),
        (".*ABS.*", "fdm_filament_abs"),
        (".*ASA @MK4S 0.*", "Prusa Generic ASA @MK4S"),
        (".*ASA @MK4S HF0.4.*", "Prusa Generic ASA @MK4S"),
        (".*ASA @MK4S HF0..*", "Prusa Generic ASA @MK4S HF0.4"),
        (".*ASA.*", "fdm_filament_asa"),
        (".*PETG @MK4S 0.*", "Prusa Generic PETG @MK4S"),
        (".*PETG @MK4S HF0.4.*", "Prusa Generic PETG @MK4S"),
        (".*PETG @MK4S HF0..*", "Prusa Generic PETG @MK4S HF0.4"),
        (".*PETG.*", "fdm_filament_pet"),
        (".*PLA @MK4S 0.*", "Prusa Generic PLA @MK4S"),
        (".*PLA @MK4S HF0.4.*", "Prusa Generic PLA @MK4S"),
        (".*PLA @MK4S HF0..*", "Prusa Generic PLA @MK4S HF0.4"),
        (".*PLA Silk @MK4S 0.*", "Prusa Generic PLA Silk @MK4S"),
        (".*PLA Silk @MK4S.*", "Prusa Generic PLA @MK4S"),
        (".*PLA.*", "fdm_filament_pla"),
        (".*TPU @MK4S 0.*", "Prusa Generic TPU @MK4S"),
        (".*TPU.*", "fdm_filament_tpu"),
    ],
}


def write_json(filename, data):
    return json.dump(data, open(filename, "w"), indent=4, sort_keys=True)


def concretize_all(out_dir):
    r = []
    for t, file_patterns in TARGETS.items():
        pattern = "|".join(file_patterns)
        for f in os.listdir(t):
            if re.fullmatch(pattern, f):
                p = os.path.join(t, f)
                data = concretize.concretize(p, [], [])
                p = os.path.join(out_dir, p)
                write_json(p, data)
                r.append(p)
    return r


def rename(filenames):
    r = []
    for fn in filenames:
        dirname = os.path.dirname(fn)
        basename = os.path.basename(fn)
        t = os.path.basename(dirname)

        newfilename = fn
        for pattern, replacement in RENAME.get(t, []):
            if not re.fullmatch(pattern, basename):
                continue

            newbase = re.sub(pattern, replacement, basename)
            newfilename = os.path.join(dirname, newbase)
            data = json.load(open(fn))
            data["name"] = newbase.replace(".json", "")
            write_json(fn, data)
            # print(f"mv \"{fn}\" \"{newfilename}\"")
            os.rename(fn, newfilename)

            # Only first match
            break

        r.append(newfilename)
    return r


def update(filename, update):
    data = json.load(open(filename))
    data.update(update)
    write_json(filename, data)


def pop(filename, key):
    data = json.load(open(filename))
    r = data.pop(key)
    write_json(filename, data)
    return r


def add_inherits(filenames):
    for fn in filenames:
        dirname = os.path.dirname(fn)
        basename = os.path.basename(fn)
        t = os.path.basename(dirname)

        for pattern, superclass in INHERITANCE.get(t, []):
            if not re.fullmatch(pattern, basename):
                continue

            data = json.load(open(fn))
            assert "inherits" not in data
            data["inherits"] = superclass
            print(f"{fn} inherits {superclass} by {pattern}")
            write_json(fn, data)

            # Only first match
            break


def minimize_all(filenames):
    for fn in filenames:
        print(fn)
        data = minimize.minimize(fn)
        write_json(fn, data)


def key_sub_list(filename, key, pattern, replacement):
    data = json.load(open(filename))
    data[key] = [re.sub(pattern, replacement, data[key][0])]
    write_json(filename, data)


def ad_hoc_preparation(out_dir):
    # key_sub_list(f"{out_dir}/machine/Original Prusa MK4 Input Shaper 0.4 nozzle.json", "printer_notes", r"(.*)MODEL_MK4IS\\nPG", r"\1MODEL_MK4S\\nPG\\nNO_TEMPLATES")
    common_data = json.load(
        open(f"{out_dir}/machine/Original Prusa MK4 Input Shaper 0.4 nozzle.json")
    )
    mk4s_data = json.load(
        open(f"{out_dir}/machine/Original Prusa MK4S 0.4 nozzle.json")
    )
    common_data["machine_start_gcode"] = mk4s_data["machine_start_gcode"]
    # common_data["printer_model"] = mk4s_data["printer_model"]
    common_data["printer_notes"] = mk4s_data["printer_notes"]
    common_data.update({"instantiation": "false", "host_type": "prusalink"})
    write_json(
        f"{out_dir}/machine/Original Prusa MK4 Input Shaper 0.4 nozzle.json",
        common_data,
    )


def compatible_printers(filenames):
    def lf(*ns):
        return [f"Prusa MK4S {n} nozzle" for n in ns]

    def hf(*ns):
        return [f"Prusa MK4S HF{n} nozzle" for n in ns]

    cmap = {
        "nozzle_diameter[0]!=0.6 and nozzle_diameter[0]!=0.8 and printer_notes!~/.*HF_NOZZLE.*/": lf(
            "0.25", "0.3", "0.4", "0.5"
        ),
        "nozzle_diameter[0]!=0.8 and nozzle_diameter[0]!=0.6": lf(
            "0.25", "0.3", "0.4", "0.5"
        )
        + hf("0.25", "0.3", "0.4", "0.5"),
        "nozzle_diameter[0]!=0.8 and nozzle_diameter[0]!=0.6 and nozzle_diameter[0]!=0.5 and printer_notes=~/.*HF_NOZZLE.*/": hf(
            "0.4"
        ),
        "nozzle_diameter[0]!=0.8 and nozzle_diameter[0]!=0.6 and printer_notes!~/.*HF_NOZZLE.*/": lf(
            "0.25", "0.3", "0.4", "0.5"
        ),
        "nozzle_diameter[0]==0.5 and printer_notes=~/.*HF_NOZZLE.*/": hf("0.5"),
        "nozzle_diameter[0]==0.6": lf("0.6") + hf("0.6"),
        "nozzle_diameter[0]==0.6 and printer_notes!~/.*HF_NOZZLE.*/": lf("0.6"),
        "nozzle_diameter[0]==0.6 and printer_notes=~/.*HF_NOZZLE.*/": hf("0.6"),
        "nozzle_diameter[0]==0.8": lf("0.8") + hf("0.8"),
        "nozzle_diameter[0]==0.8 and printer_notes!~/.*HF_NOZZLE.*/": lf("0.8"),
        "nozzle_diameter[0]==0.8 and printer_notes=~/.*HF_NOZZLE.*/": hf("0.8"),
        "nozzle_diameter[0]>=0.3 and nozzle_diameter[0]!=0.6 and nozzle_diameter[0]!=0.8": lf(
            "0.3", "0.4", "0.5"
        )
        + hf("0.4", "0.5"),
    }

    for fn in filenames:
        t = os.path.basename(os.path.dirname(fn))
        if t != "filament":
            continue

        data = json.load(open(fn))

        condition = data.pop("compatible_printers_condition")
        condition = condition.replace(
            "printer_model=~/(MK4S|MK4SMMU3|MK3.9S|MK3.9SMMU3)/ and ", ""
        )
        condition = condition.replace(" and ! single_extruder_multi_material", "")

        data["compatible_printers"] = cmap[condition]
        write_json(fn, data)


def filament_setting_id(filenames):
    for fn in filenames:
        t = os.path.basename(os.path.dirname(fn))
        if t != "filament":
            continue

        update(fn, {"setting_id": "GFSA04"})


def ad_hoc_touch_ups(out_dir, filenames):
    compatible_printers(filenames)
    filament_setting_id(filenames)

    for fn in filenames:
        t = os.path.basename(os.path.dirname(fn))
        if t != "machine":
            continue
        if "HF" in fn:
            update(fn, {"printer_model": "MK4S HF"})
        else:
            update(fn, {"printer_model": "MK4S"})

    update(
        f"{out_dir}/machine/Prusa MK4S HF0.4 nozzle.json", {"printer_variant": "0.4"}
    )
    update(
        f"{out_dir}/machine/Prusa MK4S HF0.5 nozzle.json", {"printer_variant": "0.5"}
    )
    update(
        f"{out_dir}/machine/Prusa MK4S HF0.6 nozzle.json", {"printer_variant": "0.6"}
    )
    update(
        f"{out_dir}/machine/Prusa MK4S HF0.8 nozzle.json", {"printer_variant": "0.8"}
    )

    key_sub_list(
        f"{out_dir}/machine/fdm_machine_common_mk4s.json",
        "layer_change_gcode",
        "(.*)spiral_vase(.*)",
        r"\1spiral_mode\2",
    )
    key_sub_list(
        f"{out_dir}/machine/fdm_machine_common_mk4s.json",
        "machine_start_gcode",
        "(.*)A..filament_abrasive.*; nozzle check(.*)",
        r"\1; nozzle check\2",
    )
    update(
        f"{out_dir}/machine/fdm_machine_common_mk4s.json",
        {
            "retract_when_changing_layer": "0", # https://github.com/SoftFever/OrcaSlicer/issues/7391#issuecomment-2629035206
            # Extruder clearances are in the print profile in PS
            "extruder_clearance_height_to_lid": "220",  # Set to z-height for bed which doesn't move in z
            "extruder_clearance_height_to_rod": "14",
            "extruder_clearance_radius": "45",
        },
    )

    base_start_gcode = json.load(
        open(f"{out_dir}/machine/fdm_machine_common_mk4s.json")
    )["machine_start_gcode"]
    hf_start_gcode = [re.sub(r"\[printer_model\]", "MK4S", base_start_gcode[0])]
    update(
        f"{out_dir}/machine/Prusa MK4S HF0.4 nozzle.json",
        {"machine_start_gcode": hf_start_gcode},
    )

    update(
        f"{out_dir}/filament/Prusa Generic TPU @MK4S.json", {"filament_type": ["FLEX"]}
    )
    pop(f"{out_dir}/filament/Prusa Generic ASA @MK4S.json", "filament_vendor")

    update(
        f"{out_dir}/process/process_common_mk4s.json",
        {
            "filename_format": "{input_filename_base}_{nozzle_diameter[0]}n_{layer_height}mm_{filament_type[0]}_{printer_model}_{print_time}.gcode",
            "resolution": "0",  # fdm_process_common(OS) sets this, but MK4IS_common(PS) leaves it blank
        },
    )
    for fn in filenames:
        t = os.path.basename(os.path.dirname(fn))
        if t != "process" or not os.path.basename(fn).startswith("0"):
            continue
        try:
            pop(fn, "filename_format")
        except KeyError:
            pass


def main(argv):
    out_dir = "out"

    for t in TARGETS:
        os.makedirs(os.path.join(out_dir, t), exist_ok=True)

    outfiles = concretize_all(out_dir)
    ad_hoc_preparation(out_dir)
    outfiles = rename(outfiles)
    add_inherits(outfiles)
    minimize_all(outfiles)
    ad_hoc_touch_ups(out_dir, outfiles)


if __name__ == "__main__":
    main(sys.argv)
