import argparse
import concurrent.futures as cf
import functools
import pathlib
import pickle
import sys
import threading
import time

import cv2
import Decorator as D
import ImageUtility as IU
import TimeUtility as TU

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


def setInfo(data, detector):
  image = IU.readImage(data["path"])
  if image is None:
    return False, data
  data["shape"] = image.shape
  data["pHash"] = cv2.img_hash.pHash(image)
  if detector is not None:
    _keyPoints, descriptors = detector.detectAndCompute(image, None)
    if descriptors is None:
      return False, data
    data["descriptors"] = descriptors
  return True, data


def setInfoAll(lt, ex, fails, detector):
  func = functools.partial(setInfo, detector=detector)
  rs = ex.map(func, lt)
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
    U.delKeys(other, ["descriptors", "pHash"])
    other["diff"] = diff
    sames.append(other)
    dirs[other["path"].parent]["sames"] += 1
  elif diff is None:
    others.remove(other)
    fails.append(other["path"])


def getDetector(method):
  match method:
    case "pHash":
      return cv2.img_hash.PHash().create(), None, None
    case "AKAZE(MLDB)":  # 高速?
      return (
        None,
        cv2.AKAZE_create(cv2.AKAZE_DESCRIPTOR_MLDB_UPRIGHT),
        cv2.BFMatcher_create(cv2.NORM_HAMMING, crossCheck=True),
      )
    case "AKAZE(KAZE)":  # 詳細
      return (
        None,
        cv2.AKAZE_create(cv2.AKAZE_DESCRIPTOR_KAZE_UPRIGHT),
        cv2.BFMatcher_create(cv2.NORM_L2, crossCheck=True),
      )
    case "KAZE":
      return None, cv2.KAZE_create(upright=True), cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
    case "ORB":
      return None, cv2.ORB_create(), cv2.BFMatcher_create(cv2.NORM_HAMMING, crossCheck=True)


@D.printFuncInfo()
def dumpSameImages(path, pickleOutput, failedPath, method, threshold, targetPath=None, extensions=None):
  pm = U.PickleManager(pickleOutput)
  pm.dump(path)
  pm.dump(targetPath)
  pm.dump(extensions)

  targets, others, dirs = getFiles(path, targetPath, extensions)
  phObj, detector, matcher = getDetector(method)

  fails = []
  lock = threading.Lock()
  with cf.ThreadPoolExecutor() as ex:
    start = time.perf_counter()
    U.printTime("Calculating ...")
    setInfoAll(targets, ex, fails, detector)
    if targetPath is not None:
      setInfoAll(others, ex, fails, detector)
    sec = time.perf_counter() - start
    U.printTime(TU.getTimeStr(sec), f"({sec:10.6f})")

    while len(targets) > 0:
      target = targets.pop()
      target["target"] = True
      sames = [target]
      print(f"\r\x1b[1M{len(others)}: {target['path'].parent.name} {target['path'].name}", end="")
      for other in others[:]:
        r = u.isSameImage(target, other, threshold, phObj, matcher)
        check(r, other, sames, others, fails, dirs)
      U.delKeys(target, ["descriptors", "pHash"])
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
    setInfoAll(targets, ex, fails, None)
    if targetPath is not None:
      setInfoAll(others, ex, fails, None)
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
  for x in result:
    print(f"{x[2]:5}: \n{x[0]}\n{x[1]}\n")


def setThreshold(method):
  match method:
    case "pHash":
      return 4.0
    case "AKAZE(MLDB)":  # 高速
      return 16.0
    case "AKAZE(KAZE)":  # 詳細
      return 0.04
    case "KAZE":
      return 0.04
    case "ORB":
      return 30.0


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-t", "--targetPath", type=pathlib.Path, default=None)
  parser.add_argument("-o", "--outputPath", type=pathlib.Path, default=None)
  parser.add_argument("-f", "--failedPath", type=pathlib.Path, default=None)
  parser.add_argument("-m", "--method", choices=["pHash", "AKAZE(MLDB)", "AKAZE(KAZE)", "KAZE", "ORB"], default="pHash")
  parser.add_argument("-th", "--threshold", type=float, default=None)
  parser.add_argument("-e", "--extensions", nargs="*", default=[".jpg", ".png", ".webp", ".gif"])
  args = parser.parse_args()
  path = args.path.absolute()
  if not path.exists():
    print(f'"{path}" does not exist.')
    sys.exit()

  method = args.method
  threshold = args.threshold
  if threshold is None:
    threshold = setThreshold(method)

  picklePath = pathlib.Path(path, f"pHash_{path.stem}.pkl") if args.outputPath is None else args.outputPath
  failedPath = pathlib.Path(path, f"failed_{path.stem}.pkl") if args.failedPath is None else args.failedPath
  targetPath = args.targetPath.absolute() if args.targetPath is not None else None
  return (path, picklePath, failedPath, targetPath, method, threshold, args.extensions)


def printArgs(path, picklePath, failedPath, targetPath, method, threshold, extensions):
  print(f'directory:  "{path}"')
  print(f"method:      {method}")
  print(f"threshold:   {threshold}")
  print(f'picklePath: "{picklePath}"')
  print(f'failedPath: "{failedPath}"')
  print(f'targetPath: "{targetPath}"')
  print(f'extensions: "{extensions}"\n')


if __name__ == "__main__":
  path, picklePath, failedPath, targetPath, method, threshold, extensions = argumentParser()
  printArgs(path, picklePath, failedPath, targetPath, method, threshold, extensions)

  # comparePHash(path, failedPath, targetPath)
  dumpSameImages(path, picklePath, failedPath, method, threshold, targetPath, extensions)

  rsip.printSameImagePickle(picklePath)
  printArgs(path, picklePath, failedPath, targetPath, method, threshold, extensions)
