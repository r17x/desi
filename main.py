from edifice import App, Label, TextInput, HBoxView, Window, component, use_state

METERS_TO_FEET = 3.28084

@component
def MyApp(self):

    meters, meters_set = use_state("0.0")

    meters_label_style = {"width": 170}
    feet_label_style = {"margin-left": 20, "width": 220}
    input_style = {"padding": 2, "width": 120}

    with Window():
        with HBoxView(style={"padding": 10}):
            Label("Hello:", style=meters_label_style)
            TextInput(meters, style=input_style, on_change=meters_set)
            try:
                feet = f"{float(meters) * METERS_TO_FEET :.3f}"
                Label(f"Measurement in feet: {feet}", style=feet_label_style)
            except ValueError: # Could not convert string to float
                pass # So don't render the Label

if __name__ == "__main__":
    App(MyApp()).start()
