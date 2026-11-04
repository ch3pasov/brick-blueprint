"""Pinhole camera in LDraw coordinates; output coordinates are PDF points.

Camera Z points toward the eye. The vector visibility kernel needs an affine
depth on the image plane, so use d*z/(d-z), not linearly interpolated world Z.
This is d*d / eye_distance - d: a scaled inverse depth, in target-plane LDU.
"""
import math


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


class PerspectiveCamera:
    """A square-pixel pinhole camera using the supplied orthonormal basis.

    The FOV parameter defines focal length from the full page height. With an
    explicitly shifted principal point it is a centred-equivalent angle; the
    actual page angular spans are recorded separately. By default the optical
    centre is the viewport centre. Camera roll is already in the supplied basis.
    No 2D warp or anisotropic resize is applied. Explicit cameras must keep all
    geometry in front of the near plane and inside the viewport; this illustrator
    does not slice models.
    """
    def __init__(self, vertices, right, down, backward, width, height, viewport,
                 *, field_of_view=None, camera_distance=None, camera_target=None,
                 scale=None, near_clip=.1, principal_point=None):
        self.basis = (right, down, backward)
        self.field_of_view = 30. if field_of_view is None else field_of_view
        if not math.isfinite(self.field_of_view) or not .1 <= self.field_of_view <= 120:
            raise ValueError('Field of view must be 0.1..120 degrees')
        if not math.isfinite(near_clip) or near_clip <= 0:
            raise ValueError('Near clip distance must be positive')
        self.near_clip = near_clip
        if camera_distance is not None:
            if not math.isfinite(camera_distance) or camera_distance <= 0:
                raise ValueError('Camera distance must be positive')
            if scale is not None:
                raise ValueError('Choose camera distance or scale, not both')
        if camera_target is None:
            points = [tuple(dot(v, b) for b in self.basis) for v in vertices]
            middle = [(min(v[k] for v in points)+max(v[k] for v in points))/2 for k in range(3)]
            self.target = tuple(sum(middle[k]*self.basis[k][j] for k in range(3)) for j in range(3))
        else:
            if len(camera_target) != 3 or not all(math.isfinite(v) for v in camera_target):
                raise ValueError('Camera target must contain three finite LDraw coordinates')
            self.target = tuple(camera_target)
        points = [self.camera_coordinates(v) for v in vertices]
        vx, vy, vw, vh = viewport
        if principal_point is not None:
            if len(principal_point) != 2 or not all(math.isfinite(v) for v in principal_point):
                raise ValueError('Principal point must contain two finite page coordinates')
            if camera_distance is None:
                raise ValueError('An explicit principal point requires an explicit camera distance')
        self.explicit_principal_point = principal_point is not None
        self.principal_point = tuple(principal_point) if principal_point is not None else (vx+vw/2, vy+vh/2)
        self.focal_length = height/(2*math.tan(math.radians(self.field_of_view)/2))
        self.page_angular_spans = (
            math.degrees(math.atan((width-self.principal_point[0])/self.focal_length)-math.atan(-self.principal_point[0]/self.focal_length)),
            math.degrees(math.atan((height-self.principal_point[1])/self.focal_length)-math.atan(-self.principal_point[1]/self.focal_length)))
        # Every vertex must satisfy |f*x/(d-z)| <= viewport half-width, etc.
        required = max(max(z+self.focal_length*abs(x)/(vw/2),
                           z+self.focal_length*abs(y)/(vh/2),
                           z+near_clip*1.001) for x, y, z in points)
        self.distance = (camera_distance if camera_distance is not None else
                         self.focal_length/scale if scale is not None else
                         max(required, near_clip)* (1+1e-12))
        self.eye = tuple(t+self.distance*b for t, b in zip(self.target, backward))
        self.points_per_ldu = self.focal_length/self.distance
        self.minimum_depth = min(self.distance-z for x, y, z in points)
        if self.minimum_depth <= near_clip:
            raise ValueError('Geometry crosses the camera near plane; increase camera distance or reduce scale')
        cx, cy = self.principal_point
        if any(not (vx-1e-8 <= cx+self.focal_length*x/(self.distance-z) <= vx+vw+1e-8) or
               not (vy-1e-8 <= cy+self.focal_length*y/(self.distance-z) <= vy+vh+1e-8) for x, y, z in points):
            raise ValueError('Model does not fit at requested scale/camera; increase distance or field of view')
        # Conservative upper bound on the projection Jacobian over the model.
        # Used only by the optional tiny-crease filter, never for visibility.
        radius = max(math.hypot(x, y) for x, y, z in points)
        self.detail_scale_bound = self.focal_length/self.minimum_depth * math.sqrt(1+(radius/self.minimum_depth)**2)

    def camera_coordinates(self, vertex):
        relative = sub(vertex, self.target)
        return tuple(dot(relative, b) for b in self.basis)

    def project(self, vertex):
        x, y, z = self.camera_coordinates(vertex)
        q = self.distance-z
        if q <= self.near_clip:
            raise ValueError('Geometry crosses the camera near plane')
        return (self.principal_point[0]+self.focal_length*x/q,
                self.principal_point[1]+self.focal_length*y/q,
                self.distance*z/q)

    def conditional_visible(self, points):
        # Control points are not physical geometry. Preserve uncertain edges
        # when a control point lies behind the eye/near plane.
        if any(self.distance-self.camera_coordinates(p)[2] <= self.near_clip for p in points[2:]):
            return True
        a, b, u, v = [self.project(p) for p in points]
        side = lambda p: (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        return side(u)*side(v) >= -1e-9/256  # legacy XY is 4x PDF points

    def receipt(self):
        return {'projection':'perspective', 'model':'pinhole',
                'field_of_view_vertical_degrees':self.field_of_view,
                'focal_length_points':self.focal_length,
                'distance_ldu':self.distance, 'target_ldu':self.target,
                'position_ldu':self.eye, 'principal_point_points':self.principal_point,
                'near_clip_ldu':self.near_clip, 'minimum_geometry_eye_distance_ldu':self.minimum_depth,
                'right':self.basis[0], 'down':self.basis[1],
                'depth_encoding':'d*z/(d-z); affine scaled inverse eye distance',
                'scale_definition':'points per LDU at the camera target plane',
                'fit':'camera distance only; no post-projection scale or warp',
                'near_plane_policy':'reject crossing geometry; no model slicing',
                'field_of_view_status':'tool setting, not a recovered LEGO constant',
                **({'field_of_view_definition':'centred-equivalent vertical angle defining focal length; shifted page spans recorded separately',
                    'horizontal_page_span_degrees':self.page_angular_spans[0],
                    'vertical_page_span_degrees':self.page_angular_spans[1]} if self.explicit_principal_point else {})}
