import argparse
import concurrent.futures as cf
import functools
import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import WindowsApi as WinApi
from PIL import Image, ImageTk

import ImageDiffViewer
import Utility as U
import utility as u


class FrameTitle(ttk.Frame):
  def __init__(self, root, master):
    super().__init__(master)
    self.root = root
    self.labelDirectory = ttk.Label(
      self,
      text=self.master.directory,
      style="front.TLabel",
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
    self.labelDirectory.pack(side=tk.LEFT, fill=tk.BOTH)

  def close(self):
    self.root.destroy()

  def minimize(self):
    self.root.wm_overrideredirect(False)
    self.root.iconify()


class FrameCommand(ttk.Frame):
  def __init__(self, master):
    super().__init__(master)

    self.buttonNext = ttk.Button(
      self,
      text="next",
      takefocus=True,
      command=self.master.next,
      style="front.TButton",
    )
    self.buttonPrevious = ttk.Button(
      self,
      text="previous",
      takefocus=True,
      command=self.master.previous,
      style="front.TButton",
    )
    self.buttonPerform = ttk.Button(
      self,
      text="perform",
      command=self.master.perform,
      style="back.TButton",
    )
    self.buttonUndo = ttk.Button(
      self,
      text="undo",
      command=self.master.undo,
      style="back.TButton",
    )
    self.buttonExplorer = ttk.Button(
      self,
      text="explorer",
      command=self.master.explorer,
      style="front.TButton",
    )

    self.labelRemainCount = ttk.Label(
      self,
      textvariable=self.master.svRemainCount,
      style="front.TLabel",
    )

    self.labelTargetCount = ttk.Label(
      self,
      textvariable=self.master.svTargetCount,
      style="front.TLabel",
    )
    self.labelRecordCount = ttk.Label(
      self,
      textvariable=self.master.svRecordCount,
      style="front.TLabel",
    )

    self.labelRow = ttk.Label(self, text="Row")
    self.spinboxRow = ttk.Spinbox(
      self,
      from_=1,
      to=10,
      increment=1,
      textvariable=self.master.ivRow,
      width=3,
      font=("", 18),
      state="readonly",
      command=self.master.draw,
    )
    self.labelColumn = ttk.Label(self, text="Column")
    self.spinboxColumn = ttk.Spinbox(
      self,
      from_=1,
      to=20,
      increment=1,
      textvariable=self.master.ivColumn,
      width=3,
      font=("", 18),
      state="readonly",
      command=self.master.draw,
    )

    self.comboboxColor = ttk.Combobox(
      self,
      values=["black", "white", "red", "green", "blue", "cyan", "magenta", "yellow", ""],
      textvariable=self.master.svColor,
      width=8,
    )
    self.comboboxColor.bind("<<ComboboxSelected>>", self.master.draw)
    self.buttonImageDiffViewer = ttk.Button(
      self,
      text="imageDiffViewer",
      command=self.master.callImageDiffViewer,
      style="front.TButton",
    )

    self.buttonExplorer.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.buttonUndo.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.labelRecordCount.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.buttonPerform.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.buttonNext.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.buttonPrevious.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.labelRemainCount.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.spinboxColumn.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.labelColumn.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.spinboxRow.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.labelRow.pack(side=tk.RIGHT, fill=tk.BOTH)
    self.labelTargetCount.pack(side=tk.RIGHT, fill=tk.BOTH)

    self.comboboxColor.pack(side=tk.LEFT, fill=tk.BOTH)
    self.buttonImageDiffViewer.pack(side=tk.LEFT, fill=tk.BOTH)


class CanvasWindow(tk.Canvas):
  def __init__(self, master, width, height):
    super().__init__(master)
    self.width = width
    self.height = height

    self.frameWindow = ttk.Frame(self)
    self.configure(scrollregion=(0, 0, 0, height))
    self.thumbnailSize = []
    self.thumbnails = []
    self.idWindow = None
    self.widgets = []

  def setThumbnailSize(self):
    self.thumbnailSize = [self.width // self.master.ivColumn.get(), self.height // self.master.ivRow.get()]

  def expandArea(self, num):
    row = -(-num // self.master.ivColumn.get())
    row -= self.master.ivRow.get()
    row = max(row, 0)
    appendSize = self.thumbnailSize[1] * row
    self.configure(height=self.height + appendSize)
    self.configure(scrollregion=(0, 0, 0, self.height + appendSize))
    if self.idWindow is not None:
      self.delete(self.idWindow)

    self.idWindow = self.create_window(
      (0, 0),
      window=self.frameWindow,
      anchor=tk.NW,
      width=self.width,
      height=self.height + appendSize,
    )

  def deleteAllWidgets(self):
    if len(self.widgets) <= 0:
      return
    for tp in self.widgets:
      for widget in tp:
        widget.destroy()
    self.widgets = []
    self.thumbnails = []
    self.master.targets = []
    self.master.checkedWidgetIndices = []

  def createAllCanvas(self, files, dataIndex):
    images = self.openImages(files)
    row = 0
    column = 0
    for i, file in enumerate(files):
      if i != 0 and i % self.master.ivColumn.get() == 0:
        row += 1
        column = 0
      self.createCanvas(i, row, column, file, images[i], dataIndex)
      column += 1

  def openImage(self, path):
    image = Image.open(path["path"])
    return u.resizeImage(image, *self.thumbnailSize)

  def openImages(self, data):
    with cf.ThreadPoolExecutor() as ex:
      results = ex.map(self.openImage, data)
      return list(results)

  def createCanvas(self, i, row, column, data, image, dataIndex):
    canvas = tk.Canvas(self.frameWindow, width=self.thumbnailSize[0], height=self.thumbnailSize[1], bg="gray80")
    checkValue = tk.BooleanVar(value=False)
    canvas.bind("<Button-1>", lambda _event: self.setTarget(checkValue, dataIndex, i, True))
    parent = data["path"].parent.relative_to(self.master.directory)

    checkbutton = ttk.Checkbutton(
      canvas,
      variable=checkValue,
      onvalue=True,
      offvalue=False,
      command=lambda: self.setTarget(checkValue, dataIndex, i),
    )
    image = ImageTk.PhotoImage(image, master=canvas)
    self.thumbnails.append(image)
    canvas.create_image(self.thumbnailSize[0] // 2, self.thumbnailSize[1] // 2, image=image, anchor=tk.CENTER)
    canvas.create_text(
      5,
      30,
      text=f"{parent}\n{data['path'].name}\n{data['shape']}\n{data.get('diff', '')}",
      anchor=tk.NW,
      font=("fixed", 14, "bold"),
      fill=self.master.svColor.get(),
    )
    canvas.place(
      anchor=tk.NW,
      x=column * self.thumbnailSize[0],
      y=row * self.thumbnailSize[1],
      width=self.thumbnailSize[0],
      height=self.thumbnailSize[1],
    )
    checkbutton.place(x=2, y=2, anchor=tk.NW)
    self.widgets.append((canvas, checkbutton))

  def setTarget(self, checkValue, indexData, index, fromCanvas=False):
    checked = checkValue.get()
    if fromCanvas:
      checked = not checked
      checkValue.set(checked)
    if checked:
      self.master.targets.append((indexData, index))
      self.master.checkedWidgetIndices.append(index)
    else:
      self.master.targets.remove((indexData, index))
      self.master.checkedWidgetIndices.remove(index)
    self.master.updateTargetCount()

  def deleteWidgets(self):
    for index in self.master.checkedWidgetIndices:
      for widget in self.widgets[index]:
        widget.destroy()


class SameImageViewer(ttk.Frame):
  def __init__(self, dumpFilePath, outputPath, recordPath, master=None):
    super().__init__(master)
    self.resolution = WinApi.getDisplaysResolution()[0]  # (width, height)
    self.config(width=self.resolution[0], height=self.resolution[1])
    self.master.geometry(u.toGeometry(self.resolution[0], self.resolution[1], 0, 0))
    self.master.title("SameImageViewer")
    self.pack()
    self.master.wm_overrideredirect(True)

    self.dumpFile = dumpFilePath
    self.destination = outputPath.absolute()
    self.recordPath = recordPath.absolute()
    self.pm = None
    self.data = []
    self.record = []
    self.directory = None
    self.countDataWidth = 0
    self.current = 0
    self.countData = 0
    self.countImage = 0
    self.isAutoSize = True
    self.load()

    self.setStyle()

    self.widgets = []
    self.widgetSizes = {}
    self.thumbnails = []
    self.targets = []
    self.checkedWidgetIndices = []

    self.frameTitle = FrameTitle(self.master, self)
    self.svRemainCount = tk.StringVar(self)
    self.updateRemainCount()
    self.svTargetCount = tk.StringVar(self)
    self.updateTargetCount()
    self.svRecordCount = tk.StringVar(self)
    self.svColor = tk.StringVar(self)
    self.svColor.set("red")

    self.ivRow = tk.IntVar(self, 2)
    self.ivColumn = tk.IntVar(self, 2)
    self.frameCommand = FrameCommand(self)

    titleBarHeight = 30  # 23  # 31
    frameCommandHeight = 30
    self.canvasWindow = CanvasWindow(
      self,
      width=self.resolution[0] - 20,
      height=self.resolution[1] - (frameCommandHeight + titleBarHeight),
    )
    self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvasWindow.yview)
    self.canvasWindow.configure(yscrollcommand=self.scrollbar.set)

    self.frameTitle.place(anchor=tk.NW, x=0, y=0, width=self.resolution[0], height=titleBarHeight)
    self.frameCommand.place(
      anchor=tk.NW,
      x=0,
      y=30,
      width=self.resolution[0],
      height=frameCommandHeight,
    )
    self.scrollbar.place(
      anchor=tk.NW,
      x=self.resolution[0] - 20,
      y=(frameCommandHeight + titleBarHeight),
      width=20,
      height=self.resolution[1] - (frameCommandHeight + titleBarHeight),
    )
    self.canvasWindow.place(
      anchor=tk.NW,
      x=0,
      y=(frameCommandHeight + titleBarHeight),
      width=self.resolution[0] - 20,
      height=self.resolution[1] - (frameCommandHeight + titleBarHeight),
    )
    self.canvasWindow.configure(scrollregion=(0, 0, 0, self.resolution[1] - (frameCommandHeight + titleBarHeight)))
    self.master.wm_attributes("-transparentcolor", "gray")
    self.setBind()
    self.liftTop()
    self.draw(True)

  def setStyle(self):
    self.style = ttk.Style()
    self.font = ("BIZ UDゴシック", 16)
    self.style.theme_use("clam")
    self.style.configure("TLabel", background="light cyan", font=self.font)
    self.style.configure("front.TLabel", background="turquoise", font=("", 16, "bold"))
    self.style.configure("TButton", font=("", 10), padding=[0, 0, 0, 0])
    self.style.map(
      "front.TButton",
      background=[
        ("pressed", "blue"),
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

  def setBind(self):
    self.master.bind("<Configure>", self.onOverRidereDirect)
    self.master.bind("<KeyPress-Escape>", lambda _event: self.frameTitle.buttonClose.invoke())
    self.master.bind("<MouseWheel>", self.scroll)
    self.master.bind("<KeyPress-Return>", lambda _event: self.frameCommand.buttonPerform.invoke())
    self.master.bind("<KeyPress-7>", lambda event: self.changeRow(event, 1))
    self.master.bind("<KeyPress-4>", lambda event: self.changeRow(event, -1))
    self.master.bind("<KeyPress-9>", lambda event: self.changeColumn(event, 1))
    self.master.bind("<KeyPress-6>", lambda event: self.changeColumn(event, -1))
    self.master.bind("<KeyPress-Down>", lambda _event: self.frameTitle.buttonMinimize.invoke())
    self.master.bind("<KeyPress-2>", lambda _event: self.frameTitle.buttonMinimize.invoke())
    self.master.bind("<KeyPress-Left>", lambda _event: self.frameCommand.buttonPrevious.invoke())
    self.master.bind("<KeyPress-1>", lambda _event: self.frameCommand.buttonPrevious.invoke())
    self.master.bind("<KeyPress-Right>", lambda _event: self.frameCommand.buttonNext.invoke())
    self.master.bind("<KeyPress-3>", lambda _event: self.frameCommand.buttonNext.invoke())
    self.master.bind("<KeyPress-e>", lambda _event: self.frameCommand.buttonExplorer.invoke())
    self.master.bind("<KeyPress-.>", lambda _event: self.frameCommand.buttonExplorer.invoke())
    self.master.bind("<KeyPress-z>", self.undo)
    self.master.bind("<KeyPress-->", self.undo)
    self.master.bind("<KeyPress-d>", lambda _event: self.frameCommand.buttonImageDiffViewer.invoke())
    self.master.bind("<KeyPress-0>", lambda _event: self.frameCommand.buttonImageDiffViewer.invoke())

  def onOverRidereDirect(self, _event):
    if self.master.state() == "normal":
      self.master.wm_overrideredirect(True)

  def load(self):
    self.pm = U.PickleManager(self.dumpFile)
    data = self.pm.loadExternal()
    self.directory = data[0]
    self.data = data[1:]
    self.countData = self.pm.count - 1
    self.countDataWidth = len(str(self.countData))
    maxImage = functools.reduce(max, map(len, self.data))
    self.maxImageWidth = len(str(maxImage))
    self.destination.mkdir(exist_ok=True)
    self.checkData()

  def checkData(self):  # sort?
    for i, lt in enumerate(self.data[:]):
      lt.sort(key=lambda x: x["path"])
      for dt in lt[:]:
        if not dt["path"].exists():
          self.data[i].remove(dt)
    self.data = list(filter(lambda x: len(x) > 1, self.data))
    self.countData = len(self.data)
    self.countDataWidth = len(str(self.countData))
    self.countFile = sum(map(len, self.data))
    self.countFileWidth = len(str(self.countFile))

  def draw(self, isAutoSize=False):
    self.canvasWindow.deleteAllWidgets()
    if len(self.data) <= 0:
      self.countImage = 0
      self.canvasWindow.expandArea(0)
      return
    self.countImage = len(self.data[self.current])
    if isAutoSize:
      self.autoSetSize()
    self.canvasWindow.setThumbnailSize()
    self.updateTargetCount()
    self.updateRemainCount()
    self.updateRecordCount()
    self.canvasWindow.expandArea(self.countImage)
    self.canvasWindow.createAllCanvas(self.data[self.current], self.current)

  def perform(self):
    self.canvasWindow.deleteWidgets()
    for indexData, indexFile in self.targets:
      source = self.data[indexData][indexFile]["path"]
      if not source.exists():
        print(f"not exist: {source}")
        continue
      destination = Path(self.destination, source.name)
      destination = u.checkFileName(destination)
      self.record.append((self.data[indexData][indexFile], indexData, indexFile, destination))  # indexFileは要らない
      print(f"Move:  {source!s}\n        -> {destination!s}")
      shutil.move(source, destination)
    self.targets = []
    self.updateTargetCount()
    self.updateRecordCount()
    self.deleteData()

  def deleteData(self):
    data = self.data[self.current]
    self.checkedWidgetIndices.sort()
    for i in reversed(self.checkedWidgetIndices):
      data.pop(i)
    self.data[self.current] = data
    self.checkedWidgetIndices = []
    self.countImage = len(self.data[self.current])
    self.updateTargetCount()

  def scroll(self, event):
    # scrollregionが0でも移動する
    self.canvasWindow.yview("scroll", int(-1 * (event.delta / 120)), "units")

  def next(self):
    if self.countData < 1:
      return
    if self.current < self.countData - 1:
      self.current += 1
    else:
      self.current = 0
    self.draw(True)

  def previous(self):
    if self.countData < 1:
      return
    if self.current > 0:
      self.current -= 1
    else:
      self.current = self.countData - 1
    self.draw(True)

  def updateTargetCount(self):
    self.svTargetCount.set(f"{len(self.targets):0{self.maxImageWidth}}/{self.countImage:0{self.maxImageWidth}}")

  def updateRemainCount(self):
    self.svRemainCount.set(f"{self.current + 1:0{self.countDataWidth}}/{self.countData:0{self.countDataWidth}}")

  def updateRecordCount(self):
    self.svRecordCount.set(f"{len(self.record):0{self.countFileWidth + 1}}")

  def changeRow(self, _event, m):
    minV = self.frameCommand.spinboxRow.configure("from")[-1]
    maxV = self.frameCommand.spinboxRow.configure("to")[-1]
    n = self.ivRow.get()
    x = max(minV, min(maxV, n + m))
    self.ivRow.set(x)
    self.draw()

  def changeColumn(self, _event, m):
    minV = self.frameCommand.spinboxColumn.configure("from")[-1]
    maxV = self.frameCommand.spinboxColumn.configure("to")[-1]
    n = self.ivColumn.get()
    x = max(minV, min(maxV, n + m))
    self.ivColumn.set(x)
    self.draw()

  def writeRecord(self):
    with self.recordPath.open("w", encoding="utf_8") as file:
      for data, _, _, destination in self.record:
        file.write(f"{data['path']}, {destination}\n")

  def undo(self, _event):
    if len(self.record) < 1:
      return
    data, indexData, indexFile, destination = self.record.pop()  # indexFileは要らない
    self.data[indexData].append(data)
    self.data[indexData].sort(key=lambda x: x["path"])
    shutil.move(destination, data["path"])
    self.draw()

  def autoSetSize(self):
    if not self.isAutoSize:
      return
    row, column = u.getMinFactorPair(self.countImage)
    if self.resolution[0] < self.resolution[1]:
      row, column = column, row
    self.ivRow.set(row)
    self.ivColumn.set(column)

  def explorer(self):
    if len(self.targets) < 1:
      return
    for indexData, indexFile in self.targets:
      cmd = ["explorer", self.data[indexData][indexFile]["path"].parent]
      subprocess.Popen(cmd)

  def liftTop(self):
    self.master.attributes("-topmost", True)
    self.master.attributes("-topmost", False)
    self.focus_set()

  def callImageDiffViewer(self, _event=None):
    if len(self.targets) < 2:
      return
    self.ImageDiffViewerRoot = tk.Toplevel(self)
    files = [self.data[indexData][indexFile]["path"] for indexData, indexFile in self.targets]
    # self.imageDiffViewer = ImageDiffViewer.ImageDiffViewer(None, files, master=self.ImageDiffViewerRoot)
    self.ImageDiffViewer = ImageDiffViewer.ImageDiffViewer(None, files, master=self.ImageDiffViewerRoot)


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("dumpFile", type=Path)
  parser.add_argument("-o", "--outputPath", type=Path)
  parser.add_argument("-r", "--recordPath", type=Path)
  args = parser.parse_args()
  dumpFilePath = args.dumpFile.absolute()
  pm = U.PickleManager(dumpFilePath)
  pm.countExternal()
  directory = pm.load(0)
  outputPath = Path(directory, "output") if args.outputPath is None else args.outputPath
  recordPath = Path(directory, r"output\record.txt") if args.recordPath is None else args.recordPath
  return dumpFilePath, outputPath, recordPath


if __name__ == "__main__":
  dumpFilePath, outputPath, recordPath = argumentParser()
  print(f'dumpFilePath: "{dumpFilePath}"\noutputPath:   "{outputPath}"\nrecordPath:   "{recordPath}"')
  gui = SameImageViewer(dumpFilePath, outputPath, recordPath)
  gui.mainloop()
  gui.writeRecord()
  print(f'dumpFilePath: "{dumpFilePath}"\noutputPath:   "{outputPath}"\nrecordPath:   "{recordPath}"')
  u.callExplorer([outputPath])
  u.callExplorer([recordPath])
