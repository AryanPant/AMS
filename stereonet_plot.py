import numpy as np
import matplotlib.pyplot as plt
import mplstereonet
import io
from PIL import Image
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource

def mean_orientation(D, I):
    x = np.mean(np.cos(np.radians(D)) * np.cos(np.radians(I)))
    y = np.mean(np.sin(np.radians(D)) * np.cos(np.radians(I)))
    z = np.mean(np.sin(np.radians(I)))
    mean_I = np.degrees(np.arctan2(z, np.sqrt(x**2 + y**2)))
    mean_D = np.degrees(np.arctan2(y, x)) % 360
    return mean_D, mean_I

def pole_to_plane(D, I):
    strike = (D + 90) % 360
    dip = 90 - I
    return strike, dip

def equal_area_projection(dec, inc):
    dec_rad = np.radians(dec)
    inc_rad = np.radians(inc)
    r = np.sqrt(2) * np.sin(np.radians(90 - inc) / 2)  # Schmidt Net
    x = r * np.sin(dec_rad)
    y = r * np.cos(dec_rad)
    return x, y

def create_stereonet_image(strike_dip_list, colors):
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'stereonet'})
    ax.grid(True, linestyle="--", alpha=0.5)
    for (strike, dip), color in zip(strike_dip_list, colors):
        ax.plane(strike, dip, color=color, linewidth=2)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300, bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)

    image = Image.open(buf).convert("RGBA")
    img_array = np.array(image)
    buf.close()

    img_array = np.flipud(img_array)  # Flip for Bokeh
    if np.all(img_array[:, :, 3] == 0):
        img_array[:, :, 3] = 255  # ensure visible alpha

    img_rgba = np.dstack([img_array[:, :, i] for i in range(4)])
    img_rgba = img_rgba.view(dtype=np.uint32).reshape(img_array.shape[0], img_array.shape[1])
    return img_rgba, img_array.shape[1], img_array.shape[0]

def create_stereonet_plot(df):
    D_k1, I_k1 = df["D_k1"], df["I_k1"]
    D_k2, I_k2 = df["D_k2"], df["I_k2"]
    D_k3, I_k3 = df["D_k3"], df["I_k3"]

    mean_D_k1, mean_I_k1 = mean_orientation(D_k1, I_k1)
    mean_D_k2, mean_I_k2 = mean_orientation(D_k2, I_k2)
    mean_D_k3, mean_I_k3 = mean_orientation(D_k3, I_k3)

    strike_k1, dip_k1 = pole_to_plane(mean_D_k1, mean_I_k1)
    strike_k2, dip_k2 = pole_to_plane(mean_D_k2, mean_I_k2)
    strike_k3, dip_k3 = pole_to_plane(mean_D_k3, mean_I_k3)

    img_rgba, img_width, img_height = create_stereonet_image(
        [(strike_k1, dip_k1), (strike_k2, dip_k2), (strike_k3, dip_k3)],
        ["red", "green", "blue"]
    )

    x_k1, y_k1 = equal_area_projection(D_k1, I_k1)
    x_k2, y_k2 = equal_area_projection(D_k2, I_k2)
    x_k3, y_k3 = equal_area_projection(D_k3, I_k3)

    source_k1 = ColumnDataSource(data={"x": x_k1, "y": y_k1, "D": D_k1, "I": I_k1})
    source_k2 = ColumnDataSource(data={"x": x_k2, "y": y_k2, "D": D_k2, "I": I_k2})
    source_k3 = ColumnDataSource(data={"x": x_k3, "y": y_k3, "D": D_k3, "I": I_k3})

    p = figure(width=600, height=600, title="Equal-Area Stereonet",
               match_aspect=True, tools="pan,wheel_zoom,reset,save")

    p.x_range.start, p.x_range.end = -1.2, 1.2
    p.y_range.start, p.y_range.end = -1.2, 1.2

    p.image_rgba(image=[img_rgba], x=[-1.2], y=[-1.2], dw=[2.4], dh=[2.4])

    p.scatter("x", "y", source=source_k1, size=10, color="red", marker="square",
              line_color="black", line_width=1.5)
    p.scatter("x", "y", source=source_k2, size=10, color="green", marker="triangle",
              line_color="black", line_width=1.5)
    p.scatter("x", "y", source=source_k3, size=10, color="blue", marker="circle",
              line_color="black", line_width=1.5)

    p.grid.visible = False
    p.axis.visible = False

    return p
