import argparse
import pathlib

import Utility as U


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  args = parser.parse_args()
  return args.path


if __name__ == "__main__":
  path = argumentParser()
  pm = U.PickleManager(path)
  data = pm.loadExternal()
  U.customPrint(data.pop(0))
  print(pm.count)
  print(sum(map(len, data)))
  for obj in data[1:]:
    U.customPrint(obj)
