"""
02_build_label_mapping.py

Maps FSC22's 27 fine-grained classes down to the simplified classes Forest Guard's
acoustic model actually needs to output:

    Normal / Environmental   -> background: rain, wind, birds, insects, thunderstorm, fire crackle, etc.
    Chainsaw_Threat          -> chainsaw, axe, handsaw, tree falling / wood chopping (logging signature)
    Human_Activity           -> speaking, footsteps, clapping, coughing, etc.
    Vehicle                  -> engine, car, truck, motorcycle sounds
    Animal                   -> non-threat wildlife sounds (bird calls, mammal sounds, insects)
    Generator_Mechanical     -> generator / other machinery NOT chainsaw-related (optional 6th class;
                                 merge into Chainsaw_Threat if you want a simpler 5-class problem)

IMPORTANT: The dictionary below uses class NAMES exactly as commonly documented for
FSC22 (axe, chainsaw, handsaw, generator, fire, thunderstorm, rain, wind, footsteps,
speaking, etc.) but dataset versions on Kaggle have occasionally varied slightly in
exact spelling/capitalization. Before trusting this mapping:

  1. Run 01_explore_dataset.py first and print your actual metadata CSV.
  2. Compare every "Class Name" string in your CSV against the keys below.
  3. Fix any mismatches (this script will warn you about unmapped classes when you
     run 03_extract_features.py against your real metadata).
"""

import pandas as pd

# EDIT this dict once you've confirmed real class names from your metadata CSV.
# Left side = exact Class Name string from FSC22 metadata (case-insensitive match used below)
# Right side = simplified Forest Guard class
# Verified against the REAL FSC22 metadata CSV (27 classes, confirmed by
# Ujwal's actual dataset run): Fire, Rain, Thunderstorm, WaterDrops, Wind,
# Silence, TreeFalling, Helicopter, VehicleEngine, Axe, Chainsaw, Generator,
# Handsaw, Firework, Gunshot, WoodChop, Whistling, Speaking, Footsteps,
# Clapping, Insect, Frog, BirdChirping, WingFlaping, Lion, WolfHowl, Squirrel
CLASS_NAME_TO_SIMPLIFIED = {
    # --- Forest Threat (logging / fire signature) ---
    "fire": "Fire_Threat",
    "firework": "Fire_Threat",
    "axe": "Chainsaw_Threat",
    "chainsaw": "Chainsaw_Threat",
    "handsaw": "Chainsaw_Threat",
    "treefalling": "Chainsaw_Threat",
    "woodchop": "Chainsaw_Threat",
    "gunshot": "Chainsaw_Threat",
    # Generator merged into Chainsaw_Threat: only ~45 train samples on its own,
    # too few to reliably learn as a separate class, and not a primary threat
    # category for the demo narrative anyway.
    "generator": "Chainsaw_Threat",

    # --- Vehicle ---
    "helicopter": "Vehicle",
    "vehicleengine": "Vehicle",

    # --- Human ---
    "whistling": "Human_Activity",
    "speaking": "Human_Activity",
    "footsteps": "Human_Activity",
    "clapping": "Human_Activity",

    # --- Environmental / weather ---
    "rain": "Normal_Environmental",
    "thunderstorm": "Normal_Environmental",
    "waterdrops": "Normal_Environmental",
    "wind": "Normal_Environmental",
    "silence": "Normal_Environmental",

    # --- Animal ---
    "insect": "Animal",
    "frog": "Animal",
    "birdchirping": "Animal",
    "wingflaping": "Animal",
    "lion": "Animal",
    "wolfhowl": "Animal",
    "squirrel": "Animal",
}


def normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def build_mapping_from_metadata(metadata_df, class_name_col="Class Name"):
    """
    Takes the actual FSC22 metadata DataFrame (loaded in script 01) and returns:
      - a dict {class_id: simplified_label}
      - a list of any class names it could NOT map (you must fill these in above)
    """
    id_col_candidates = [c for c in metadata_df.columns if "class" in c.lower() and "id" in c.lower()]
    name_col_candidates = [c for c in metadata_df.columns if "class" in c.lower() and "name" in c.lower()]
    if not id_col_candidates or not name_col_candidates:
        raise ValueError(
            f"Could not auto-detect Class ID / Class Name columns. "
            f"Columns available: {list(metadata_df.columns)}. Edit this function to match."
        )
    id_col, name_col = id_col_candidates[0], name_col_candidates[0]

    mapping = {}
    unmapped = []
    for _, row in metadata_df.iterrows():
        raw_name = str(row[name_col])
        norm_name = normalize(raw_name)
        simplified = CLASS_NAME_TO_SIMPLIFIED.get(norm_name)
        if simplified is None:
            unmapped.append(raw_name)
            simplified = "UNMAPPED"
        mapping[str(row[id_col])] = simplified

    if unmapped:
        print("\n⚠️  The following class names from your real metadata CSV are NOT yet")
        print("   mapped in CLASS_NAME_TO_SIMPLIFIED — add them before running feature extraction:")
        for u in sorted(set(unmapped)):
            print(f"     - {u!r}")

    return mapping


if __name__ == "__main__":
    # quick standalone check against a metadata CSV path
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "fsc22_data/Metadata.csv"
    df = pd.read_csv(csv_path)
    mapping = build_mapping_from_metadata(df)
    print("\nFinal Class ID -> Simplified Label mapping:")
    for k, v in sorted(mapping.items(), key=lambda x: int(x[0])):
        print(f"  {k}: {v}")
