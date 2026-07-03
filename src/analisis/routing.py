import json
import math
import networkx as nx
from shapely.geometry import shape, Point, LineString, mapping, box, Polygon
from shapely.ops import unary_union
from src.spatial.projection import reproject_geojson, to_wgs84, to_utm

ROAD_SPEEDS = {
    "motorway": 80, "trunk": 60, "primary": 50, "secondary": 40,
    "tertiary": 30, "residential": 25, "living_street": 15,
    "unclassified": 20, "service": 15,
    "motorway_link": 50, "trunk_link": 40,
    "primary_link": 40, "secondary_link": 30, "tertiary_link": 25
}
DEFAULT_SPEED = 20

class RoadNetwork:
    _instance = None

    @classmethod
    def get_instance(cls, path: str = "geojson/vias_completas.geojson"):
        if cls._instance is None:
            cls._instance = cls(path)
        return cls._instance

    def __init__(self, path: str = "geojson/vias_completas.geojson"):
        with open(path, encoding="utf-8") as f:
            vias_wgs84 = json.load(f)

        self.vias_utm = reproject_geojson(vias_wgs84, to_crs="epsg:32720", from_crs="epsg:4326")
        self.graph = self._build_graph()
        self.node_positions = {n: data for n, data in self.graph.nodes(data=True)}

    def _build_graph(self):
        G = nx.Graph()
        features = self.vias_utm.get("features", [])
        road_segments = []

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry")
            if not geom or geom["type"] != "LineString":
                continue
            coords = geom["coordinates"]
            if len(coords) < 2:
                continue

            highway_type = props.get("highway", "unclassified")
            speed = ROAD_SPEEDS.get(highway_type, DEFAULT_SPEED)
            oneway = props.get("oneway", "no") == "yes"

            segments = []
            for i in range(len(coords) - 1):
                x1, y1 = coords[i][:2]
                x2, y2 = coords[i + 1][:2]
                dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                time_h = dist / (speed * 1000)
                time_min = time_h * 60
                segments.append({
                    "start": (round(x1, 2), round(y1, 2)),
                    "end": (round(x2, 2), round(y2, 2)),
                    "dist_m": dist,
                    "time_min": time_min,
                    "highway": highway_type,
                    "name": props.get("name", "")
                })

            road_segments.extend(segments)
            if oneway:
                G.add_edges_from([
                    (s["start"], s["end"], {
                        "weight": s["dist_m"], "time_min": s["time_min"],
                        "highway": s["highway"], "name": s["name"]
                    })
                    for s in segments
                ])
            else:
                G.add_edges_from([
                    (s["start"], s["end"], {
                        "weight": s["dist_m"], "time_min": s["time_min"],
                        "highway": s["highway"], "name": s["name"]
                    })
                    for s in segments
                ])
                G.add_edges_from([
                    (s["end"], s["start"], {
                        "weight": s["dist_m"], "time_min": s["time_min"],
                        "highway": s["highway"], "name": s["name"]
                    })
                    for s in segments
                ])

        return G

    def find_nearest_node(self, x_utm: float, y_utm: float) -> tuple:
        pt = Point(x_utm, y_utm)
        min_dist = float("inf")
        nearest = None
        for node in self.graph.nodes():
            d = pt.distance(Point(node))
            if d < min_dist:
                min_dist = d
                nearest = node
        return nearest, min_dist

    def get_isochrone_nodes(self, x_utm: float, y_utm: float, max_dist_m: float) -> list:
        source_node, _ = self.find_nearest_node(x_utm, y_utm)
        if source_node is None:
            return []

        lengths = nx.single_source_dijkstra_path_length(self.graph, source_node, cutoff=max_dist_m, weight="weight")
        reachable = list(lengths.keys()) + [source_node]
        return reachable

    def get_reachable_area(self, x_utm: float, y_utm: float, max_dist_m: float) -> object:
        nodes = self.get_isochrone_nodes(x_utm, y_utm, max_dist_m)
        if not nodes:
            return None

        points = [Point(n) for n in nodes]
        if len(points) == 1:
            return points[0].buffer(100)
        elif len(points) == 2:
            return unary_union(points).buffer(100)

        from scipy.spatial import ConvexHull
        import numpy as np
        pts_array = np.array([(n[0], n[1]) for n in nodes])
        try:
            hull = ConvexHull(pts_array)
            hull_pts = [nodes[i] for i in hull.vertices]
            hull_poly = Polygon(hull_pts)
            return hull_poly.buffer(200)
        except Exception:
            return unary_union([p.buffer(200) for p in points])
