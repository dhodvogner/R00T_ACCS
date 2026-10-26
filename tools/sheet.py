"""contact sheet of screenshots/t_*.png  (dev helper)"""
import glob
import os
import sys

import cv2
import numpy as np

root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
files = sorted(glob.glob(os.path.join(root, "t_*.png")))
w = int(sys.argv[1]) if len(sys.argv) > 1 else 400
ims = []
for f in files:
    im = cv2.imread(f)
    im = cv2.resize(im, (w, int(im.shape[0] * w / im.shape[1])), interpolation=cv2.INTER_AREA)
    cv2.putText(im, os.path.basename(f)[2:-4], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
    ims.append(im)
per = int(sys.argv[2]) if len(sys.argv) > 2 else 4
while len(ims) % per:
    ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + per]) for i in range(0, len(ims), per)]
cv2.imwrite(os.path.join(root, "sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(len(files), "shots")
