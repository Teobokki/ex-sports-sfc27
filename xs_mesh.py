"""procedural mesh helpers (numpy -> GeomNode) and the standard character shading."""
import numpy as np
from panda3d.core import (GeomVertexFormat, GeomVertexArrayFormat, GeomVertexData, GeomTriangles, Geom, GeomNode, InternalName, Material)

_FMT = None


def _fmt():
    global _FMT
    if _FMT is None:
        af = GeomVertexArrayFormat()
        af.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        af.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        af.add_column(InternalName.get_color(), 4, Geom.NT_float32, Geom.C_color)
        af.add_column(InternalName.get_tangent(), 4, Geom.NT_float32, Geom.C_vector)
        _FMT = GeomVertexFormat.register_format(GeomVertexFormat(af))
    return _FMT


def mesh_node(name, V, N, C, T, tris):
    """numpy arrays -> GeomNode (v3 n3 c4 t4 interleaved)"""
    n = len(V)
    vd = GeomVertexData(name, _fmt(), Geom.UH_static); vd.unclean_set_num_rows(n)
    arr = np.concatenate([V, N, C, T], 1).astype(np.float32)
    memoryview(vd.modify_array(0)).cast("B")[:] = arr.tobytes()
    tr = GeomTriangles(Geom.UH_static); tr.set_index_type(Geom.NT_uint32)
    ta = tr.modify_vertices(); ta.unclean_set_num_rows(len(tris) * 3)
    memoryview(ta).cast("B")[:] = np.asarray(tris, np.uint32).ravel().tobytes()
    g = Geom(vd); g.add_primitive(tr); gn = GeomNode(name); gn.add_geom(g); return gn


_COL = {}


def shade(np_, app, gloss=0.2, sheen=0.0):
    import xs_shaders
    xs_shaders.apply(np_, app, gloss=gloss, sheen=sheen)
    mt = Material("prop"); mt.set_base_color((1, 1, 1, 1)); mt.set_roughness(0.7); np_.set_material(mt, 1)
    return np_


# ================================================================ v1.0.4 JP TAXI driver (adult Indian man)
DAN_HEAD_O = (0.0, -0.030, 1.578)
DAN_HEAD_R = ((0.955854594707489, -0.2752596139907837, -0.10283010452985764), (0.2674517035484314, 0.9599443078041077, -0.08352530002593994),
              (0.12170232087373734, 0.0523359552025795, 0.9911858439445496))
