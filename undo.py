import argparse
import pathlib
import shutil


def read(path):
  with path.open("r", encoding="utf_8") as file:
    data = file.read()
    return data.splitlines()


def undo(lines):
  n = len(str(len(lines)))
  for i, line in enumerate(lines):
    source, destination = line.split(", ")
    if pathlib.Path(destination).exists():
      print(f"Move {i:{n}}:  {destination!s}\n        -> {source!s}")
      shutil.move(destination, source)


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("recordPath", type=pathlib.Path)
  return parser.parse_args()


if __name__ == "__main__":
  args = argumentParser()
  lines = read(args.recordPath)
  print(lines)
  undo(lines)
