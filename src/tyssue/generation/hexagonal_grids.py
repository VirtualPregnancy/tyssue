"""
Hexagonal grids
---------------
"""
from math import tau

import numpy as np
import pandas as pd

from ..config.geometry import flat_sheet, planar_sheet
from .utils import make_df


def hexa_grid2d(nx, ny, distx, disty, noise=None):
    """Creates an hexagonal grid of points"""
    cy, cx = np.mgrid[0:ny+2, 0:nx+2]
    cx = cx.astype(float)
    cy = cy.astype(float)
    cx[::2, :] += 0.5

    centers = np.vstack([cx.flatten(), cy.flatten()]).astype(float).T
    centers[:, 0] *= distx
    centers[:, 1] *= disty
    if noise is not None:
        pos_noise = np.random.normal(scale=noise, size=centers.shape)
        centers += pos_noise
    return centers


def hexa_grid3d(nx, ny, nz, distx=1.0, disty=1.0, distz=1.0, noise=None):
    """Creates an hexagonal grid of points"""
    cz, cy, cx = np.mgrid[0:nz, 0:ny, 0:nx]
    cx = cx.astype(float)
    cy = cy.astype(float)
    cz = cz.astype(float)
    cx[:, ::2] += 0.5
    cy[::2, :] += 0.5
    cy *= np.sqrt(3) / 2
    cz *= np.sqrt(3) / 2

    centers = np.vstack([cx.flatten(), cy.flatten(), cz.flatten()]).T
    centers[:, 0] *= distx
    centers[:, 1] *= disty
    centers[:, 2] *= distz
    if noise is not None:
        pos_noise = np.random.normal(scale=noise, size=centers.shape)
        centers += pos_noise
    return centers


def circle(num_t, radius=1.0, phase=0.0):
    """Returns x and y positions of `num_t` points regularly placed around a circle
    of radius `radius`, shifted by `phase` radians.

    Parameters
    ----------
    num_t : int
        the number of points around the circle
    radius : float, default 1.
        the radius of the circle
    phase : float, default 0.0
        angle shift w/r to the x axis in radians

    Returns
    -------
    points : np.Ndarray of shape (num_t, 2), the x, y positions of the points

    """
    if not num_t:
        return np.zeros((1, 2))

    theta = np.arange(0, tau, tau / num_t)
    return np.vstack([radius * np.cos(theta + phase), radius * np.sin(theta + phase)]).T


def hexa_disk(num_t, radius=1):
    """Returns an arrays of x, y positions of points evenly spread on
    a disk with num_t points on the periphery.

    Parameters
    ----------
    num_t : int
        the number of poitns on the disk periphery, the rest of the disk is
        filled automaticaly
    radius : float, default 1.
        the radius of the disk

    """

    n_circles = int(np.ceil(num_t / tau) + 1)
    if not n_circles:
        return np.zeros((1, 2))

    num_ts = np.linspace(num_t, 0, n_circles, dtype=int)
    rads = radius * num_ts / num_t
    phases = np.pi * num_ts / num_t
    return np.concatenate(
        [circle(n, r, phi) for n, r, phi in zip(num_ts, rads, phases)]
    )


def hexa_cylinder(
    num_t, num_z, radius=1.0, capped=False, noise=0, orientation="transverse"
):
    """Returns an arrays of x, y positions of points evenly spread on
    a cylinder with num_t points on the periphery and num_z points on its length.

    Parameters
    ----------
    num_t : int,
        The number of points on the periphery
    num_z : int,
        The number of points along the z axis (the length of the cylinder)
    radius : float, default 1
        The radius of the cylinder
    capped : bool, default False
        If True, the tips of the cylinder are capped by a disk of point
        as generated by the `hexa_disk` function.
    noise : float, default 0
        normaly distributed position noise around the cell points
    orientation : {'transverse' | 'longitudinal'}, default 'transverse'
        the orientation of the cells (with the longueur axis
        perpendicular or along the length of the cylinder)


    """
    delta_t = tau / num_t
    if orientation == "transverse":
        points_zt = hexa_grid2d(num_z, num_t, delta_t, delta_t, noise=noise)
    elif orientation == "longitudinal":
        points_tz = hexa_grid2d(num_t, num_z, delta_t, delta_t, noise=noise)
        points_zt = np.vstack((points_tz[:, 1], points_tz[:, 0])).T
    else:
        raise ValueError(
            f"Orientation should either be 'transverse' or 'longitudinal',"
            f" not {orientation}"
        )

    points_zt[:, 0] = points_zt[:, 0] * radius
    zs = points_zt[:, 0]
    xs = radius * np.cos(points_zt[:, 1])
    ys = radius * np.sin(points_zt[:, 1])
    points_xyz = np.vstack((xs - xs.mean(), ys - ys.mean(), zs - zs.mean())).T

    if capped:

        disk = hexa_disk(num_t, radius)[num_t:, :]
        left_cap = np.zeros((disk.shape[0], 3))
        left_cap[:, :2] = disk
        left_cap[:, 2] = points_xyz[:, 2].min()  # - delta_t  # * 0.5

        right_cap = np.zeros((disk.shape[0], 3))
        right_cap[:, :2] = disk
        right_cap[:, 2] = points_xyz[:, 2].max()  # + delta_t  # * 0.5
        points_xyz = np.concatenate([left_cap, points_xyz, right_cap])

    return points_xyz


"""

Three cells sheet
-----------------
"""


def three_faces_sheet_array():
    """
    Creates the apical junctions mesh of three packed hexagonal faces.
    If `zaxis` is `True` (defaults to False), adds a `z` coordinates,
    with `z = 0`.

    Faces have a side length of 1.0 +/- 1e-3.

    Returns
    -------

    points: (13, ndim) np.array of floats
      the positions, where ndim is 2 or 3 depending on `zaxis`
    edges: (15, 2)  np.array of ints
      indices of the edges
    (Nc, Nv, Ne): triple of ints
      number of faces, vertices and edges (3, 13, 15)

    """
    Nc = 3  # Number of faces
    points = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [1.5, 0.866],
            [1.0, 1.732],
            [0.0, 1.732],
            [-0.5, 0.866],
            [-1.5, 0.866],
            [-2, 0.0],
            [-1.5, -0.866],
            [-0.5, -0.866],
            [0, -1.732],
            [1, -1.732],
            [1.5, -0.866],
        ]
    )

    edges = np.array(
        [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
            [4, 5],
            [5, 0],
            [5, 6],
            [6, 7],
            [7, 8],
            [8, 9],
            [9, 0],
            [9, 10],
            [10, 11],
            [11, 12],
            [12, 1],
        ]
    )

    Nv, Ne = len(points), len(edges)
    return points, edges, (Nc, Nv, Ne)


def three_faces_sheet(zaxis=True):
    """
    Creates the apical junctions mesh of three packed hexagonal faces.
    If `zaxis` is `True` (defaults to False), adds a `z` coordinates,
    with `z = 0`.

    Faces have a side length of 1.0 +/- 1e-3.

    Returns
    -------

    face_df: the faces `DataFrame` indexed from 0 to 2
    vert_df: the junction vertices `DataFrame`
    edge_df: the junction edges `DataFrame`

    """
    points, _, (Nc, Nv, Ne) = three_faces_sheet_array()

    if zaxis:
        coords = ["x", "y", "z"]
    else:
        coords = ["x", "y"]

    face_idx = pd.Index(range(Nc), name="face")
    vert_idx = pd.Index(range(Nv), name="vert")

    _edge_e_idx = np.array(
        [
            [0, 1, 0],
            [1, 2, 0],
            [2, 3, 0],
            [3, 4, 0],
            [4, 5, 0],
            [5, 0, 0],
            [0, 5, 1],
            [5, 6, 1],
            [6, 7, 1],
            [7, 8, 1],
            [8, 9, 1],
            [9, 0, 1],
            [0, 9, 2],
            [9, 10, 2],
            [10, 11, 2],
            [11, 12, 2],
            [12, 1, 2],
            [1, 0, 2],
        ]
    )

    edge_idx = pd.Index(range(_edge_e_idx.shape[0]), name="edge")

    if zaxis:
        specifications = flat_sheet()
    else:
        specifications = planar_sheet()

    # ## Faces DataFrame
    face_df = make_df(index=face_idx, spec=specifications["face"])

    # ## Junction vertices and edges DataFrames
    vert_df = make_df(index=vert_idx, spec=specifications["vert"])
    edge_df = make_df(index=edge_idx, spec=specifications["edge"])

    edge_df["srce"] = _edge_e_idx[:, 0]
    edge_df["trgt"] = _edge_e_idx[:, 1]
    edge_df["face"] = _edge_e_idx[:, 2]

    vert_df.loc[:, coords[:2]] = points
    if zaxis:
        vert_df.loc[:, coords[2:]] = 0.0

    datasets = {"face": face_df, "vert": vert_df, "edge": edge_df}
    return datasets, specifications
