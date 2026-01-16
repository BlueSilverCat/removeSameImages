import argparse
import pathlib

import Utility as U


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-k", "--sortKey", choices=["path", "count"])
  args = parser.parse_args()
  return args.path, args.sortKey


def printSameImagePickle(path, sortKey="count"):
  pm = U.PickleManager(path)
  data = pm.loadExternal()
  directory = data.pop(0)
  print(directory)
  print(f"same images: {pm.count}")
  print(f"total:       {sum(map(len, data))}")
  counter = {}
  for lt in data:
    for dt in lt:
      U.countDict(counter, str(dt["path"].parent.relative_to(directory)))
  width = max(len(str(v)) for v in counter.values())

  dt = (
    sorted(counter.items(), key=lambda x: x[1], reverse=True)
    if sortKey == "count"
    else sorted(counter.items(), key=lambda x: x[0], reverse=True)
  )
  for k, v in dt:
    print(f"{v:{width}}: {k}")


if __name__ == "__main__":
  path, sortKey = argumentParser()
  printSameImagePickle(path, sortKey)
