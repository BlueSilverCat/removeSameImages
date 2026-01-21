import argparse
import concurrent.futures as cf
import pathlib
import pickle
import sys
import threading

import cv2

import readSameImagePickle as rsip
import Utility as U
import utility as u


def getFiles(path, targetPath, extensions=None):
  if extensions is None:
    extensions = [".jpg", ".png", ".webp", ".gif"]
  if targetPath is not None:
    targets, targetDirs = u.getFiles(targetPath, isRecurse=True, extensions=extensions)
    others, otherDirs = u.getFiles(path, isRecurse=True, extensions=extensions)
    targets = U.subList(targets, others)
    others = U.subList(others, targets)
    dirs = targetDirs | otherDirs
  else:
    targets, dirs = u.getFiles(path, isRecurse=True, extensions=extensions)
    others = targets
  return targets, others, dirs


def setInfo(data):
  image = u.readImage(data["path"])
  if image is None:
    return False, data
  data["shape"] = image.shape
  data["pHash"] = cv2.img_hash.pHash(image)
  return True, data


def setInfoAll(lt, ex, fails):
  rs = ex.map(setInfo, lt)
  for result in rs:
    success, data = result
    if not success:
      fails.append(data["path"])
      lt.remove(data)


def dump(pm, obj, lock):
  with lock:
    pm.dump(obj)


def check(result, other, sames, others, fails, dirs):
  isSame, diff = result
  if isSame:
    others.remove(other)
    other["diff"] = diff
    sames.append(other)
    dirs[other["path"].parent]["sames"] += 1
  elif diff is None:
    others.remove(other)
    fails.append(other["path"])


def dumpSameImages(path, pickleOutput, failedPath, targetPath=None, threshold=9.0, extensions=None):
  pm = U.PickleManager(pickleOutput)
  pm.dump(path)
  pm.dump(targetPath)
  pm.dump(extensions)
  targets, others, dirs = getFiles(path, targetPath, extensions)
  lock = threading.Lock()
  phObj = cv2.img_hash.PHash().create()
  fails = []
  with cf.ThreadPoolExecutor() as ex:
    print("Calculate pHash...")
    setInfoAll(targets, ex, fails)
    if targetPath is not None:
      setInfoAll(others, ex, fails)
    while len(targets) > 0:
      target = targets.pop()
      target["target"] = True
      sames = [target]
      print(f"\r\x1b[1M{len(others)}: {target['path'].parent.name} {target['path'].name}", end="")
      for other in others[:]:
        r = u.isSameImage(target, other, phObj, threshold)
        check(r, other, sames, others, fails, dirs)
      U.delKeys(target, ["pHash"])
      if len(sames) > 1:
        dirs[target["path"].parent]["sames"] += 1
        ex.submit(dump, pm, sames, lock)
  pm.dump(dirs)
  print()
  if len(fails) > 1:
    print(f"fails: {fails}")
    with failedPath.open("wb") as file:
      pickle.dump(fails, file)


def getPHashDiff(target, other, phObj=None):
  diff = u.comparePHash(target["pHash"], other["pHash"], phObj)
  return target["path"], other["path"], diff


def comparePHash(path, failedPath, targetPath=None, extensions=None):
  targets, others, _ = getFiles(path, targetPath, extensions)
  phObj = cv2.img_hash.PHash().create()
  fails = []
  result = []
  with cf.ThreadPoolExecutor() as ex:
    setInfoAll(targets, ex, fails)
    if targetPath is not None:
      setInfoAll(others, ex, fails)
    while len(targets) > 0:
      target = targets.pop()
      target["target"] = True
      print(f"\r\x1b[1M{len(others)}: {target['path'].parent.name} {target['path'].name}", end="")
      result.extend([getPHashDiff(target, other, phObj) for other in others])
  print()
  if len(fails) > 1:
    print(f"fails: {fails}")
    with failedPath.open("wb") as file:
      pickle.dump(fails, file)
  print(path)
  print(targetPath)
  for x in result:
    print(f"{x[2]:5}: {U.subPath(x[0], targetPath)} {U.subPath(x[1], path)}")


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-t", "--targetPath", type=pathlib.Path, default=None)
  parser.add_argument("-o", "--outputPath", type=pathlib.Path, default=None)
  parser.add_argument("-f", "--failedPath", type=pathlib.Path, default=None)
  parser.add_argument("-th", "--threshold", type=float, default=9.0)
  parser.add_argument("-e", "--extensions", nargs="*", default=[".jpg", ".png", ".webp", ".gif"])
  args = parser.parse_args()
  path = args.path.absolute()
  if not path.exists():
    print(f'"{path}" does not exist.')
    sys.exit()

  picklePath = pathlib.Path(path, f"pHash_{path.stem}.pkl") if args.outputPath is None else args.outputPath
  failedPath = pathlib.Path(path, f"failed_{path.stem}.pkl") if args.failedPath is None else args.failedPath
  targetPath = args.targetPath.absolute() if args.targetPath is not None else None
  return (path, picklePath, failedPath, targetPath, args.threshold, args.extensions)


if __name__ == "__main__":
  path, picklePath, failedPath, targetPath, threshold, extensions = argumentParser()
  print(f'directory:  "{path}"\nthreshold:   {threshold}\npicklePath: "{picklePath}"')
  print(f'failedPath: "{failedPath}"\ntargetPath: "{targetPath}\nextensions: "{extensions}"')

  # comparePHash(path, failedPath, targetPath)
  dumpSameImages(path, picklePath, failedPath, targetPath, threshold, extensions)
  rsip.printSameImagePickle(picklePath)
  print(f'directory:  "{path}"\nthreshold:   {threshold}\npicklePath: "{picklePath}"')
  print(f'failedPath: "{failedPath}"\ntargetPath: "{targetPath}\nextensions: "{extensions}"')
