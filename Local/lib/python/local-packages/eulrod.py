#!/usr/bin/env python
import sys
import argparse
import numpy as np

np.set_printoptions(precision=3)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("axis", nargs=3, type=float,
        help="Axis of rotation [default: %(default)s]")
    parser.add_argument("theta",
        help="Angle of rotation [default: %(default)s]")
    parser.add_argument("--deg", default=False, action="store_true",
        help="Input angle is in degrees [default: %(default)s]")
    args = parser.parse_args(argv)
    axis = np.array(args.axis)
    theta = eval(args.theta, {"__builtin__": None}, {"pi": np.pi})
    if args.deg:
        theta *= np.pi / 180

    Rij = rotation_matrix(axis, theta)


def rotation_matrix(axis, theta):
    axis = axis / np.sqrt(np.dot(axis, axis))
    a = np.cos(theta / 2)
    b, c, d = -axis * np.sin(theta / 2)
    return np.array([
        [a * a + b * b-c * c-d * d, 2 * (b * c-a * d), 2 * (b * d + a * c)],
        [2 * (b * c + a * d), a * a + c * c-b * b-d * d, 2 * (c * d-a * b)],
        [2 * (b * d-a * c), 2 * (c * d + a * b), a * a + d * d-b * b-c * c]])


if __name__ == "__main__":
    sys.exit(main())
