import os
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.models import Span, ColumnDataSource, FreehandDrawTool, MultiLine, Button, CustomJS
from bokeh.layouts import column, row

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"asc"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data(filename):
    input_file = os.path.join(UPLOAD_FOLDER, filename)

    # Read the file
    with open(input_file, "r") as file:
        lines = file.readlines()

    data = []
    for line in lines:
        parts = [p.strip() for p in line.split() if p.strip()]
        if parts:
            data.append(parts)

    rows_per_specimen = 22
    structured_data = []

    for i in range(0, len(data), rows_per_specimen):
        specimen = data[i:i + rows_per_specimen]
        if len(specimen) >= 12:
            n = i // rows_per_specimen + 1
            try:
                k1 = float(specimen[11][0])
                k2 = float(specimen[11][1])
                k3 = float(specimen[11][2])
                Mean_sus = float(specimen[8][2])
                structured_data.append([n, k1, k2, k3, Mean_sus])
            except (IndexError, ValueError) as e:
                print(f"Error processing specimen {n}: {e}")

    df = pd.DataFrame(structured_data, columns=["n", "k1", "k2", "k3", "Mean_sus"])
    df["Kmean"] = df[["k1", "k2", "k3"]].mean(axis=1)
    df["P"] = df["k1"] / df["k3"]
    df["T"] = (2 * np.log(df["k2"] / df["k3"])) / np.log(df["k1"] / df["k3"]) - 1

    return df

@app.route("/", methods=["GET", "POST"])
def index():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".asc")]
    selected_file = request.form.get("file_select")

    if request.method == "POST" and selected_file:
        df = load_data(selected_file)
        kmean_values = df["Mean_sus"] * 10**6  # Convert Mean Susc to *10^6

        # ColumnDataSource for FreehandDrawTool
        source = ColumnDataSource(data=dict(xs=[], ys=[]))

        # **Graph 1: P vs T**
        p1 = figure(title=f"P vs T",
                    x_axis_label='P',
                    y_axis_label='T',
                    width=400,
                    height=400,
                    tools="pan,box_zoom,zoom_in,zoom_out,reset,save,hover,tap,box_select,undo,redo")

        p1.scatter(x=df["P"], y=df["T"], color="cyan", size=14, marker="diamond", line_color="black")
        p1.multi_line(xs='xs', ys='ys', source=source, line_width=2, line_color='blue')
        hline = Span(location=0, dimension='width', line_color='black', line_dash='dashed', line_width=1)
        p1.add_layout(hline)
        freehand_tool = FreehandDrawTool(renderers=[p1.renderers[-1]])
        p1.add_tools(freehand_tool)
        p1.toolbar.active_drag = freehand_tool

        # **Graph 2: N vs Mean Susc. (Histogram)**
        hist, edges = np.histogram(kmean_values, bins=6)
        p2 = figure(title="N vs Mean Susc.",
                    x_axis_label="Mean Susc * 10^6",
                    y_axis_label="N",
                    width=400,
                    height=400,
                    tools="pan,box_zoom,zoom_in,zoom_out,reset,save,hover,tap,box_select,undo,redo")

        p2.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="purple", line_color="black", alpha=0.8)
        p2.multi_line(xs='xs', ys='ys', source=source, line_width=2, line_color='blue')
        freehand_tool2 = FreehandDrawTool(renderers=[p2.renderers[-1]])
        p2.add_tools(freehand_tool2)
        p2.toolbar.active_drag = freehand_tool2

        # **Graph 3: P vs Mean Susc.**
        p3 = figure(title="P vs Mean Susc.",
                    x_axis_label='Mean Susc. x 10^6',
                    y_axis_label='P',
                    width=400,
                    height=400,
                    tools="pan,box_zoom,zoom_in,zoom_out,reset,save,hover,tap,box_select,undo,redo")

        p3.scatter(x=kmean_values, y=df['P'], color='cyan', size=14, marker="diamond", line_color='black')
        p3.multi_line(xs='xs', ys='ys', source=source, line_width=2, line_color='blue')
        p3.y_range.start = 1
        p3.y_range.end = 1.5
        freehand_tool3 = FreehandDrawTool(renderers=[p3.renderers[-1]])
        p3.add_tools(freehand_tool3)
        p3.toolbar.active_drag = freehand_tool3

        # **Clear Button**
        clear_button = Button(label="Clear Drawings", button_type="danger")
        clear_callback = CustomJS(args=dict(source=source), code="""
            source.data = {xs: [], ys: []};  // Clear the data in the source
            source.change.emit();  // Notify Bokeh to update the plot
        """)
        clear_button.js_on_click(clear_callback)

        # **Arrange plots in rows and columns**
        layout = column(row(p1, p2), row(p3), clear_button)

        # Embed Bokeh plot
        script, div = components(layout)
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()

        return render_template(
            "index.html",
            plot_script=script,
            plot_div=div,
            js_resources=js_resources,
            css_resources=css_resources,
            files=files,
            selected_file=selected_file,
        )

    return render_template("index.html", files=files, selected_file=None)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect(request.url)

    file = request.files["file"]

    if file.filename == "" or not allowed_file(file.filename):
        return redirect(request.url)

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
