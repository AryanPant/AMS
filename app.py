import os
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.models import Span, ColumnDataSource, FreehandDrawTool, MultiLine, Button, CustomJS, HoverTool, Select, Toggle
from bokeh.layouts import column, row
from stereonet_plot import create_stereonet_plot

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
        scatter_source = ColumnDataSource(data=dict(
            P=df["P"],
            T=df["T"],
            Mean_sus=df["Mean_sus"] * 10**6
        ))

        # Create data dictionary for plot options
        plot_data = {
            'P': df['P'],
            'T': df['T'],
            'Mean_sus': df['Mean_sus'] * 10**6,
            'K1/K2': df['k1']/df['k2'],
            'K2/K3': df['k2']/df['k3'],
            'Kmean': df['Kmean']
        }

        # Add all data to scatter source
        for key, value in plot_data.items():
            scatter_source.add(value, key)

        # Create dropdown menus
        x_select = Select(
            title="X-Axis:",
            value="P",
            options=sorted(list(plot_data.keys()))
        )

        y_select = Select(
            title="Y-Axis:",
            value="T",
            options=sorted(list(plot_data.keys()))
        )

        # Create unified plot
        p = figure(
            title="Interactive Plot",
            width=800,
            height=600,
            tools="pan,box_zoom,zoom_in,zoom_out,reset,save,tap,box_select,undo,redo"
        )

        # Add scatter plot
        scatter = p.scatter(
            x=x_select.value,
            y=y_select.value,
            source=scatter_source,
            color='cyan',
            size=14,
            marker="diamond",
            line_color='black'
        )

        # Add freehand drawing
        source_draw = ColumnDataSource(data=dict(xs=[], ys=[]))
        p.multi_line(xs='xs', ys='ys', source=source_draw, line_width=2, line_color='blue')
        freehand_tool = FreehandDrawTool(renderers=[p.renderers[-1]])
        p.add_tools(freehand_tool)
        p.toolbar.active_drag = freehand_tool

        # Add hover tool
        hover = HoverTool(
            tooltips=[
                ("X", f"@{x_select.value}{{0.000}}"),
                ("Y", f"@{y_select.value}{{0.000}}")
            ],
            mode='mouse'
        )
        p.add_tools(hover)

        # Add clear button
        clear_button = Button(label="Clear Drawing", button_type="danger")
        clear_callback = CustomJS(args=dict(source=source_draw), code="""
            source.data = {xs: [], ys: []};
            source.change.emit();
        """)
        clear_button.js_on_click(clear_callback)

        # Add axis update callback
        callback = CustomJS(args=dict(
            plot=p,
            scatter=scatter,
            source=scatter_source,
            x_select=x_select,
            y_select=y_select,
            hover=hover
        ), code="""
            // Update scatter plot
            scatter.glyph.x = {field: x_select.value};
            scatter.glyph.y = {field: y_select.value};
            
            // Update axis labels
            plot.xaxis.axis_label = x_select.value;
            plot.yaxis.axis_label = y_select.value;
            
            // Update hover tooltips
            hover.tooltips = [
                ["X", "@" + x_select.value + "{0.000}"],
                ["Y", "@" + y_select.value + "{0.000}"]
            ];
            const selected = source.selected.indices;
            source.selected.indices = [];
            source.change.emit();
            setTimeout(() => {
                source.selected.indices = selected;
                source.change.emit();
            }, 50);
 
            plot.change.emit();
        """)

        x_select.js_on_change('value', callback)
        y_select.js_on_change('value', callback)











        # --------- Selection Buttons (8 Toggle Buttons) ---------
        # buttons = [Button(label=f"Point {i+1}", button_type="default") for i in range(8)]

        # # JS Callback to highlight selected points
        # callback_code = """
        # var selected = source.selected.indices;
        # for (var i = 0; i < buttons.length; i++) {
        #     if (selected.includes(i)) {
        #         buttons[i].button_type = "success";
        #     } else {
        #         buttons[i].button_type = "default";
        #     }
        # }
        # """
        # scatter_source.selected.js_on_change("indices", CustomJS(args=dict(source=scatter_source, buttons=buttons), code=callback_code))

        # for i, button in enumerate(buttons):
        #     button.js_on_click(CustomJS(args=dict(source=scatter_source, index=i, button=button), code="""
        #         var selected = source.selected.indices;
        #         if (selected.includes(index)) {
        #             source.selected.indices = selected.filter(item => item !== index);
        #             button.button_type = "default";
        #         } else {
        #             selected.push(index);
        #             source.selected.indices = selected;
        #             button.button_type = "success";
        #         }
        #         source.change.emit();
        #     """))

        buttons = [Toggle(label=f"Point {i+1}", button_type="default", active=False) for i in range(8)]                  
        for i, button in enumerate(buttons):
            button.js_on_click(CustomJS(args=dict(source=scatter_source, index=i, button=button), code="""
                let selected = source.selected.indices.slice();  // Copy current selection
                const i = index;

                if (button.active) {
                    if (!selected.includes(i)) {
                        selected.push(i);
                    }
                    button.button_type = "success";
                } else {
                    selected = selected.filter(j => j !== i);
                    button.button_type = "default";
                }

                source.selected.indices = selected;
                source.change.emit();
            """))

        # JS Callback: Plot selection → Sync button states
        sync_callback = CustomJS(args=dict(source=scatter_source, buttons=buttons), code="""
            const selected = source.selected.indices;
            for (let i = 0; i < buttons.length; i++) {
                const isSelected = selected.includes(i);
                buttons[i].active = isSelected;
                buttons[i].button_type = isSelected ? "success" : "default";
            }
        """)

        scatter_source.selected.js_on_change("indices", sync_callback)

        # --------- Layout ---------
        button_row = row(*buttons, sizing_mode="stretch_width")
        layout = column(
            button_row,
            row(x_select, y_select),
            p,clear_button,
            sizing_mode="stretch_width"
        )

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