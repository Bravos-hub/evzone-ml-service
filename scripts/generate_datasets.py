from pathlib import Path

from src.ml.data.synthetic_generator import save_datasets


def main() -> None:
    out_dir = Path("src/ml/data/datasets")
    paths = save_datasets(out_dir)
    print("Generated datasets:")
    for name, p in paths.items():
        print(f" - {name}: {p}")


if __name__ == "__main__":
    main()
