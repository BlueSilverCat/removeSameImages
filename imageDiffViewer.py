import argparse
import concurrent.futures as cf
import itertools
import pathlib
import tkinter as tk
from tkinter import ttk

import Decorator as D
import WindowsApi as WinApi
from PIL import Image, ImageTk

import Utility as U
import utility as u


class FrameTitle(ttk.Frame):
  def __init__(self, root, master):
    super().__init__(master)
    self.root = root
    self.labelTitle = ttk.Label(
      self,
      text=self.root.title,
      # style="front.TLabel",
    )
    self.buttonClose = ttk.Button(
      self,
      text="close",
      takefocus=True,
      command=self.close,
      style="front.TButton",
    )
    self.buttonMinimize = ttk.Button(
      self,
      text="minimize",
      takefocus=True,
      command=self.minimize,
      style="front.TButton",
    )

    self.buttonClose.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.buttonMinimize.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.labelTitle.pack(side=tk.LEFT, fill=tk.BOTH)

  def close(self):
    self.root.destroy()

  def minimize(self):
    self.root.wm_overrideredirect(False)
    self.root.iconify()


class ImageDiffViewer(tk.Frame):
  def __init__(self, directory, paths, master=None):
    super().__init__(master)
    self.master.title = "ImageDiffViewer"
    self.resolution = WinApi.getDisplaysResolution()[0]  # (width, height)
    self.config(width=self.resolution[0], height=self.resolution[1])
    self.master.geometry(u.toGeometry(self.resolution[0], self.resolution[1], 0, 0))
    self.master.wm_overrideredirect(True)

    self.directory = directory
    self.paths = paths
    self.countFile = 0
    self.current = 0
    self.images = []

    self.frameTitle = FrameTitle(self.master, self)
    self.canvas = tk.Canvas(self, width=self.resolution[0], height=self.resolution[1], highlightthickness=0)

    self.pack()
    titleBarHeight = 30
    self.frameTitle.place(anchor=tk.NW, x=0, y=0, width=self.resolution[0], height=titleBarHeight)
    self.canvas.place(
      anchor=tk.NW,
      x=0,
      y=titleBarHeight,
      width=self.resolution[0],
      height=self.resolution[1] - titleBarHeight,
    )
    self.canvas.update()
    self.canvasSize = (self.canvas.winfo_width(), self.canvas.winfo_height())
    self.data = []
    self.countImages = 0

    self.setFiles()
    self.setBinds()
    self.setStyle()
    self.readImages()
    self.drawImage()

  def setBinds(self):
    self.master.bind("<Configure>", self.onOverRideRedirect)
    self.master.bind("<KeyPress-Right>", self.next)
    self.master.bind("<KeyPress-Left>", self.previous)
    self.master.bind("<KeyPress-Escape>", self.destroyAll)

  def setStyle(self):
    self.style = ttk.Style()
    self.font = ("BIZ UDゴシック", 16, "bold")
    self.style.theme_use("clam")
    self.style.configure("TLabel", background="light cyan", font=self.font)
    self.style.configure("front.TLabel", background="turquoise", font=("BIZ UDゴシック", 18, "bold"))
    self.style.configure("TButton", font=("BIZ UDゴシック", 10), padding=[0, 0, 0, 0])
    self.style.map(
      "front.TButton",
      background=[
        ("pressed", "blue"),
        ("active", "cyan"),
        ("!disabled", "light sky blue"),
      ],
      relief=[
        ("pressed", "sunken"),
        ("!pressed", "raised"),
      ],
    )
    self.style.map(
      "back.TButton",
      background=[
        ("pressed", "red"),
        ("active", "orange"),
        ("!disabled", "magenta1"),
      ],
      relief=[
        ("pressed", "sunken"),
        ("!pressed", "raised"),
      ],
    )

  def setFiles(self):
    if self.directory is not None:
      self.paths = U.getFiles(self.directory, False, [".jpg", ".gif", ".webp", ".png"])
    self.countFile = len(self.paths)

  def resizeImage(self, image):
    return u.resizeImage(image, self.canvasSize[0] // 3, self.canvasSize[1]), image.size

  def openImage(self, path):
    image = Image.open(path)
    image.load()
    return image

  def getImageDiff(self, index):
    i, j = index
    return (
      i,
      j,
      u.resizeImage(u.diffImage(self.images[i], self.images[j]), self.canvasSize[0] // 3, self.canvasSize[1]),
    )

  @D.printFuncInfo()
  def readImages(self):
    indices = itertools.combinations(range(self.countFile), r=2)
    with cf.ThreadPoolExecutor() as ex:
      results = ex.map(self.openImage, self.paths, timeout=60)
      self.images = list(results)
      # n = self.images == self.countFile
      results = ex.map(self.getImageDiff, indices, timeout=180)
      self.data = list(results)
      results = ex.map(self.resizeImage, self.images, timeout=60)
      self.images = list(results)
      self.countImages = len(self.data)

  def destroyAll(self, _event):
    self.master.destroy()

  def setTkImage(self, index, diffImage):
    self.tkImages = [(ImageTk.PhotoImage(self.images[i][0], master=self.canvas), self.images[i][1]) for i in index]
    self.tkImages.append((ImageTk.PhotoImage(diffImage, master=self.canvas), 0))

  @D.printFuncInfo()
  def drawImage(self):
    self.liftTop()
    self.canvas.delete("all")
    x, y, image = self.data[self.current]
    index = (x, y)
    self.setTkImage(index, image)
    width = self.canvasSize[0] // 3
    sizes = []
    for i, (image, size) in enumerate(self.tkImages):
      x = width // 2 + i * width
      self.canvas.create_image(x, self.canvasSize[1] // 2, image=image, anchor=tk.CENTER)
      sizes.append(size)
    for i, n in enumerate(index):
      self.canvas.create_text(
        i * width + 5,
        0,
        text=f"{self.paths[n].parent.name}\n{self.paths[n].name}\n{sizes[i]}",
        anchor=tk.NW,
        font=("BIZ UDゴシック", 16, "bold"),
        fill="red",
      )
    n = len(self.data)
    l = len(str(n))
    self.canvas.create_text(
      2 * width + 5,
      0,
      text=f"{self.current + 1:{l}}\n{n:{l}}",
      anchor=tk.NW,
      font=("BIZ UDゴシック", 16, "bold"),
      fill="red",
    )

  def next(self, _event):
    if self.current < self.countImages - 1:
      self.current += 1
    else:
      self.current = 0
    self.drawImage()

  def previous(self, _event):
    if self.current > 0:
      self.current -= 1
    else:
      self.current = self.countImages - 1
    self.drawImage()

  def onOverRideRedirect(self, _event):
    if self.master.state() == "normal" and not self.master.wm_overrideredirect():
      self.master.wm_overrideredirect(True)

  def liftTop(self):
    self.master.attributes("-topmost", True)
    self.master.attributes("-topmost", False)
    self.focus_set()


def argumentParser():
  parser = argparse.ArgumentParser()
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("-p", "--paths", nargs="*", type=pathlib.Path)
  group.add_argument("-d", "--directory", dest="directory", type=pathlib.Path)
  return parser.parse_args()


if __name__ == "__main__":
  args = argumentParser()
  root = tk.Tk()
  viewer = ImageDiffViewer(args.directory, args.paths, master=root)
  viewer.mainloop()
