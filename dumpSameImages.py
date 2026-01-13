import argparse
import concurrent.futures as cf
import pathlib
import threading

import cv2
import Decorator as D

import Utility as U
import utility as u

# ZeroPHash = np.array([[0, 0, 0, 0, 0, 0, 0, 0]], dtype=np.uint8)
# PHO = cv2.img_hash.PHash().create()


def getFiles(path, targetPath, extensions=None):
  if extensions is None:
    extensions = [".jpg", ".png", ".webp", ".gif"]
  if targetPath is not None:
    targets = u.getFiles(targetPath, isRecurse=True, extensions=extensions)
    others = u.getFiles(path, isRecurse=True, extensions=extensions)
    others = u.subList(others, targets)
  else:
    targets = u.getFiles(path, isRecurse=True, extensions=extensions)
    others = targets
  return targets, others


def setInfo(data):
  # with data["path"].open("rb") as f:
  #   check_chars = f.read()[-2:]
  # if check_chars != b"\xff\xd9":
  #   print("Not complete image")
  #   print(data)

  image = u.readImage(data["path"])
  if image is None:
    return False, data
  data["shape"] = image.shape
  data["pHash"] = cv2.img_hash.pHash(image)
  # data["sortKey"] = PHO.compare(ZeroPHash, ph)
  return True, data


def setInfoAll(lt, ex, fails):
  rs = ex.map(setInfo, lt)
  for result in rs:
    success, data = result
    if not success:
      fails.append(data["path"])
      lt.remove(data)


# @D.printFuncInfo()
# def dumpSameImagesSingle(directory, pm, failPath, target=None):
#   if target is not None:
#     targets = u.getFiles(target, isRecurse=True, extensions=[".jpg", ".png", ".webp"])
#     files = u.getFiles(directory, isRecurse=True, extensions=[".jpg", ".png", ".webp"])
#     files = u.subList(files, targets)
#   else:
#     targets = u.getFiles(directory, isRecurse=True, extensions=[".jpg", ".png", ".webp"])
#     files = targets

#   fails = []
#   while len(targets) > 0:
#     target = targets.pop()
#     success, targetImage = setInfo(target)
#     if not success:
#       fails.append(target["path"])

#     U.printTime(f"{len(files):5}: {target['path']!s}")
#     sames = [target]

#     for other in files[:]:
#       success, otherImage = setInfo(other)
#       if not success:
#         fails.append(other["path"])
#         files.remove(other)
#         continue
#       isSame, diff = u.isSameImage(targetImage, target["pHash"], otherImage, other["pHash"])
#       if isSame:
#         files.remove(other)
#         other["diff"] = diff
#         U.delKeys(other, ["pHash"])
#         sames.append(other)
#     U.delKeys(target, ["pHash"])
#     if len(sames) > 1:
#       pm.dump(sames)
#   U.customPrint(fails)
#   if len(fails) > 1:
#     u.dump(failPath, fails)


def dump(pm, obj, lock):
  with lock:
    pm.dump(obj)


def check(result, sames, others, fails):
  isSame, diff, other = result
  # print(isSame, diff, other["path"])
  if isSame:
    # u.remove(others, "path", other["path"])
    others.remove(other)
    other["diff"] = diff
    U.delKeys(other, ["pHash"])
    sames.append(other)
  elif diff is None:
    # u.remove(others, "path", other["path"])
    others.remove(other)
    fails.append(other["path"])


@D.printFuncInfo()
def dumpSameImages(path, pickleOutput, failedPath, targetPath=None):
  pm = U.PickleManager(pickleOutput)
  pm.dump(path)
  targets, others = getFiles(path, targetPath)
  lock = threading.Lock()
  phObj = cv2.img_hash.PHash().create()
  fails = []
  with cf.ThreadPoolExecutor() as ex:
    setInfoAll(targets, ex, fails)
    # targets.sort(key=lambda x: x["sortKey"])
    # U.customPrint(targets)
    if targetPath is not None:
      setInfoAll(others, ex, fails)
      # others.sort(key=lambda x: x["sortKey"])
    while len(targets) > 0:
      target = targets.pop()
      target["target"] = True
      sames = [target]
      print(f"\r\x1b[1M{len(others)}: {target['path'].parent.name} {target['path'].name}", end="")
      for other in others[:]:
        r = u.isSameImage(target, other, phObj)
        check(r, sames, others, fails)
      U.delKeys(target, ["pHash"])
      if len(sames) > 1:
        ex.submit(dump, pm, sames, lock)
        # pm.dump(sames)
  print()
  if len(fails) > 1:
    U.customPrint(fails)
    u.dump(failedPath, fails)


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("path", type=pathlib.Path)
  parser.add_argument("-t", "--targetPath", type=pathlib.Path, default=None)
  parser.add_argument("-o", "--outputPath", type=pathlib.Path, default=None)
  parser.add_argument("-f", "--failedPath", type=pathlib.Path, default=None)
  args = parser.parse_args()
  path = args.path.absolute()
  picklePath = pathlib.Path(path, f"pHash_{path.stem}.pkl") if args.outputPath is None else args.outputPath
  failedPath = pathlib.Path(path, f"failed_{path.stem}.pkl") if args.failedPath is None else args.failedPath
  targetPath = args.targetPath.absolute() if args.targetPath is not None else None
  return (path, picklePath, failedPath, targetPath)


if __name__ == "__main__":
  path, picklePath, failedPath, targetPath = argumentParser()
  print(f'directory:  "{path}"\npicklePath: "{picklePath}"\nfailedPath: "{failedPath}"\ntargetPath: "{targetPath}"')

  dumpSameImages(path, picklePath, failedPath, targetPath)
  pm = U.PickleManager(picklePath)
  data = pm.loadExternal()
  print(pm.count)
  print(sum(map(len, data[1:])))
  print(f'directory:  "{path}"\npicklePath: "{picklePath}"\nfailedPath: "{failedPath}"\ntargetPath: "{targetPath}"')
