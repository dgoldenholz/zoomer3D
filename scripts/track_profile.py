"""Tread side profile traced from the user's eight-wheel drawing.

The drawing's left end is the robot's front (-Y). Coordinates are in the
same construction units as robot_design.py, before its scale_xyz conversion.
"""
from math import atan2, hypot

# Cubic segments follow the centre of the white outline in the reference.
_CURVES = [
 ((80,42),(125,42),(222,42),(263,43)),
 ((263,43),(290,59),(329,76),(351,87)),
 ((351,87),(360,100),(367,115),(363,130)),
 ((363,130),(357,146),(341,153),(323,157)),
 ((323,157),(248,165),(169,167),(91,167)),
 ((91,167),(72,167),(52,160),(45,150)),
 ((45,150),(34,139),(45,111),(57,90)),
 ((57,90),(64,78),(75,53),(80,42)),
]

def reference_point(x, y):
    return ((x-202)*(.574/325), .0085+(167-y)*(.205/125))

def track_path(count=192):
    dense=[]
    for curve in _CURVES:
        for i in range(80):
            t=i/80;u=1-t
            p=[u**3*curve[0][j]+3*u*u*t*curve[1][j]+3*u*t*t*curve[2][j]+t**3*curve[3][j] for j in (0,1)]
            dense.append(reference_point(*p))
    dense.append(dense[0]);lengths=[0.0]
    for a,b in zip(dense,dense[1:]):lengths.append(lengths[-1]+hypot(b[0]-a[0],b[1]-a[1]))
    points=[];j=0
    for i in range(count):
        d=i*lengths[-1]/count
        while lengths[j+1]<d:j+=1
        t=(d-lengths[j])/(lengths[j+1]-lengths[j])
        points.append(tuple(dense[j][k]*(1-t)+dense[j+1][k]*t for k in (0,1)))
    return points

def track_samples(count=70):
    points=track_path(count)
    for i,(y,z) in enumerate(points):
        prev=points[i-1];nxt=points[(i+1)%count]
        angle=atan2(nxt[1]-prev[1],nxt[0]-prev[0])
        yield y,z,angle

# Five lower wheels, then three upper return rollers. Pixel radii interpreted
# as circular wheels, with dark hubs and blue annular faces.
_WHEELS = [
 ('drive',80,132,25,'lower'),
 ('idler_1',152,134,23,'lower'),
 ('idler_2',212,129,24,'lower'),
 ('idler_3',270,129,23,'lower'),
 ('idler_4',329,120,26,'lower'),
 ('return_1',115,75,24,'upper'),
 ('return_2',173,76,23,'upper'),
 ('return_3',233,74,22,'upper'),
]

def track_wheels():
    for name,x,y,r,row in _WHEELS:
        cy,cz=reference_point(x,y)
        yield dict(name=name,y=cy,z=cz,radius=r*(.574/325),row=row)
