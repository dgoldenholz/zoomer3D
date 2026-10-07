"""The drawing contract shared by the editor, curriculum and evaluator."""
import json
import math
from pathlib import Path
import numpy as np

COLORS = {'black': '#202733', 'red': '#e34852', 'blue': '#357bea', 'green': '#29a775'}
MARKER_WIDTH_M = 0.0015
BOARD_WIDTH_M = 0.30
BOARD_HEIGHT_M = 0.06


def validate_drawing(value):
    if not isinstance(value, dict) or value.get('version') != 1:
        raise ValueError('Expected a version 1 drawing.')
    tolerance = value.get('tolerance_m', .03)
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or not .0005 <= tolerance <= .10:
        raise ValueError('Position tolerance must be between 0.05 and 10 cm.')
    if value.get('marker_width_m', MARKER_WIDTH_M) != MARKER_WIDTH_M:
        raise ValueError('This robot uses one 1.5 mm marker width.')
    strokes = value.get('strokes')
    if not isinstance(strokes, list) or not 1 <= len(strokes) <= 500:
        raise ValueError('Draw between 1 and 500 strokes.')
    result = []
    count = 0
    for stroke in strokes:
        if not isinstance(stroke, dict) or stroke.get('color') not in COLORS:
            raise ValueError('Use black, red, blue or green.')
        points = stroke.get('points', [])
        if not isinstance(points, list) or not points:
            raise ValueError('Each stroke needs at least one point.')
        clean = []
        previous = -1
        for point in points:
            if not isinstance(point, dict):
                raise ValueError('Invalid stroke point.')
            x, y, t = (point.get(k) for k in ('x', 'y', 't_ms'))
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (x, y, t)):
                raise ValueError('Stroke coordinates and times must be finite numbers.')
            if not 0 <= x <= 1 or not 0 <= y <= 1 or t < previous or t < 0:
                raise ValueError('Points must stay on the canvas and times must increase.')
            previous = t
            clean.append(dict(x=float(x), y=float(y), t_ms=float(t)))
        count += len(clean)
        if count > 100000:
            raise ValueError('The drawing contains too many points.')
        result.append(dict(color=stroke['color'], points=clean))
    return dict(version=1, name=str(value.get('name', 'Untitled'))[:100],
                width_m=BOARD_WIDTH_M, height_m=BOARD_HEIGHT_M,
                marker_width_m=MARKER_WIDTH_M, tolerance_m=float(tolerance), strokes=result)


def load_drawing(path):
    return validate_drawing(json.loads(Path(path).read_text()))


def resample(points, spacing=.0006):
    """Remove redundant mouse samples, then bound spacing without losing corners."""
    p = np.array([[v['x'] * BOARD_WIDTH_M, (1-v['y']) * BOARD_HEIGHT_M] for v in points])
    p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-9]]
    keep={0,len(p)-1};pending=[(0,len(p)-1)]
    while pending:
        a,b=pending.pop()
        if b-a<2:continue
        delta=p[b]-p[a];length=float(delta@delta)
        t=np.clip((p[a+1:b]-p[a])@delta/max(length,1e-20),0,1)
        error=np.linalg.norm(p[a+1:b]-(p[a]+t[:,None]*delta),axis=1)
        k=int(np.argmax(error))+a+1
        if error.max()>.0001:keep.add(k);pending.extend([(a,k),(k,b)])
    p=p[sorted(keep)]
    out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        count = max(1, int(np.ceil(np.linalg.norm(b-a) / spacing)))
        out.extend(a + (b-a)*t/count for t in range(1, count+1))
    return np.array(out)


def path_errors(target, actual):
    """Ordered point correspondence, Euclidean squared error in m²."""
    target, actual = np.asarray(target), np.asarray(actual)
    if target.shape != actual.shape or target.ndim != 2 or len(target) == 0:
        raise ValueError('Expected equal, nonempty ordered point arrays.')
    squared = np.sum((target-actual)**2, axis=1)
    return dict(mse_m2=float(np.mean(squared)), rmse_m=float(np.sqrt(np.mean(squared))),
                max_error_m=float(np.sqrt(squared.max())))


def ink_quality(targets, strokes, ink, radius=.001, indices=None):
    """Compare every stroke with contact ink, including missing and stray marks."""
    from scipy.spatial import cKDTree
    target_distances=[];ink_distances=[]
    for index in range(len(targets)) if indices is None else indices:
        target=targets[index]
        actual=np.array([m['position'] for m in ink if m['stroke']==index and m['color']==strokes[index]['color']])
        if len(actual):
            target_distances.extend(cKDTree(actual[:,[0,2]]).query(target[:,[0,2]])[0])
            ink_distances.extend(cKDTree(target[:,[0,2]]).query(actual[:,[0,2]])[0])
        else:target_distances.extend([float('inf')]*len(target))
    for mark in ink:
        if mark['stroke']<0 or mark['stroke']>=len(targets):
            ink_distances.append(float('inf'))
    t=np.asarray(target_distances);a=np.asarray(ink_distances)
    return dict(target_coverage_1mm=float(np.mean(t<=radius)),
                ink_precision_1mm=float(np.mean(a<=radius)) if len(a) else 0.,
                shape_rmse_m=float(np.sqrt(np.mean(t*t))) if np.isfinite(t).all() else None,
                max_target_gap_m=float(t.max()) if np.isfinite(t).all() else None)
