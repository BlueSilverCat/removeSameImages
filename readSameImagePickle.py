import argparse
import pathlib

import Utility as U


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-k", "--sortKey", choices=["path", "count"], default="path")
  parser.add_argument("-v", "--verbose", action="store_true")
  args = parser.parse_args()
  return args.path, args.sortKey, args.verbose


def printSameImagePickle(path, sortKey="path", *, isVerbose=False):
  if not path.exists():
    print(f'"{path}" does not exist.')
    return

  pm = U.PickleManager(path)
  data = pm.loadExternal()
  directory = data.pop(0)
  target = data.pop(0)
  extensions = data.pop(0)
  dirs = data.pop()
  print(f"directory:   {directory}")
  print(f"target:      {target}")
  print(f"extensions:  {extensions}")
  wt = max(len(str(v["total"])) for v in dirs.values())
  ws = max(len(str(v["sames"])) for v in dirs.values())
  print("dirs:")
  dt = (
    sorted(filter(lambda x: x[1]["sames"] > 0, dirs.items()), key=lambda x: x[1]["sames"], reverse=True)
    if sortKey == "count"
    else sorted(filter(lambda x: x[1]["sames"] > 0, dirs.items()), key=lambda x: x[0], reverse=False)
  )
  for k, v in dt:
    print(f"{v['sames']:{wt}} / {v['total']:{ws}}: {U.subPath(k, directory)}")
  print(f"same images: {pm.count - 1}")
  print(f"total:       {sum(map(len, data))}")

  if isVerbose:
    for lt in data:
      n = len(lt)
      print(n)
      for dt in lt:
        diff = str(dt.get("target", "")) + str(dt.get("diff", ""))
        print(f"{U.subPath(dt['path'], directory)}, {dt['shape']}, {diff}")


if __name__ == "__main__":
  path, sortKey, isVerbose = argumentParser()
  printSameImagePickle(path, sortKey, isVerbose=isVerbose)
