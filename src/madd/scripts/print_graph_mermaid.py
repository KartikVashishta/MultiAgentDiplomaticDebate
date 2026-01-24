from madd.core.graph import build_graph
from pathlib import Path

app=build_graph()
g=app.get_graph()
out = Path("output")
out.mkdir(exist_ok=True)
png_path = out / "madd_graph.png"

png_bytes=g.draw_mermaid_png()
png_path.write_bytes(png_bytes)

print(f"Wrote: {png_path.resolve()}")