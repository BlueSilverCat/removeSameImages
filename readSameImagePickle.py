import argparse
import pathlib

import Utility as U


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-k", "--sortKey", choices=["path", "count"], default="path")
  args = parser.parse_args()
  return args.path, args.sortKey


def printSameImagePickle(path, sortKey="path", *, isVerbose=False):
  if not path.exists():
    print(f'"{path}" does not exist.')
    return

  pm = U.PickleManager(path)
  data = pm.loadExternal()
  directory = data.pop(0)
  print(f"directory:   {directory}")
  print(f"same images: {pm.count - 1}")
  print(f"total:       {sum(map(len, data))}")
  if pm.count < 2:  # noqa: PLR2004
    return
  counter = {}
  for lt in data:
    for dt in lt:
      U.countDict(counter, str(U.subPath(dt["path"].parent, directory)))
  width = max(len(str(v)) for v in counter.values())
  dt = (
    sorted(counter.items(), key=lambda x: x[1], reverse=True)
    if sortKey == "count"
    else sorted(counter.items(), key=lambda x: x[0], reverse=False)
  )
  for k, v in dt:
    print(f"{v:{width}}: {k}")

  if isVerbose:
    for lt in data:
      for dt in lt:
        print(dt)


if __name__ == "__main__":
  path, sortKey = argumentParser()
  printSameImagePickle(path, sortKey)
