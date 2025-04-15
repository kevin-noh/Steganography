import flet
from flet import (
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Page,
    Row,
    Column,
    Text,
    TextStyle,
    Icons,
    Switch,
    IconButton,
    Container
)
import steg
import unsteg

input_image_path = Text()
target_image_path = Text()
paths = [input_image_path, target_image_path]
save = Switch(label="Save Original Image within the Target Image", value=True)

def call_steg(e):
    if paths[0].value == None or paths[0].value == "" or \
    paths[1].value == None or paths[1].value == "":
        print("?")
    else:
        steg.init_params(paths[0].value, paths[1].value, save.value)
        output_path = steg.return_output_path(paths[1].value)
        steg.stegano_image(paths[1].value, output_path)
    
def call_unsteg(e):
    if paths[1].value == None or paths[1].value == "":
        print("?")
    else:
        if save.value:
            unsteg.init_params(None, paths[1].value)
        else:
            unsteg.init_params(paths[0].value, paths[1].value)
        unsteg.unstegano_image(paths[1].value)

def main(page: Page):
    page.title = "Steganography Test"
    page.window.width = 500
    page.window.height = 300
    
    # Pick files dialog
    def pick_input_result(e: FilePickerResultEvent):
        paths[0].value = (
            e.files[0].path if e.files else None
        )
        paths[0].update()
        
    def pick_target_result(e: FilePickerResultEvent):
        paths[1].value = (
            e.files[0].path if e.files else None
        )
        paths[1].update()

    input_image_dialog = FilePicker(on_result=pick_input_result)
    target_image_dialog = FilePicker(on_result=pick_target_result)

    # hide all dialogs in overlay
    page.overlay.extend([input_image_dialog, target_image_dialog])

    page.add(
        Row(
            [
                ElevatedButton(
                    "Input Image",
                    icon=Icons.UPLOAD_FILE,
                    on_click=lambda _: input_image_dialog.pick_files(
                        allow_multiple=False
                    ),
                ),
                paths[0],
                IconButton(
                    icon=Icons.DELETE_FOREVER_ROUNDED,
                    icon_color="pink600",
                    icon_size=30,
                    tooltip="Clear the file",
                    on_click=lambda _: ((globals()['paths'][0].__setattr__('value', None)),
                    globals()['paths'][0].update()),
                ),
            ],
            alignment=flet.MainAxisAlignment.CENTER
        ),
        Row(
            [
                ElevatedButton(
                    "Target Image",
                    icon=Icons.UPLOAD_FILE,
                    on_click=lambda _: target_image_dialog.pick_files(
                        allow_multiple=False
                    ),
                ),
                paths[1],
                IconButton(
                    icon=Icons.DELETE_FOREVER_ROUNDED,
                    icon_color="pink600",
                    icon_size=30,
                    tooltip="Clear the file",
                    on_click=lambda _: ((globals()['paths'][1].__setattr__('value', None)),
                    globals()['paths'][1].update()),
                ),
            ],
            alignment=flet.MainAxisAlignment.CENTER
        ),
        Row([save], alignment=flet.MainAxisAlignment.CENTER),
        Row(
            [
                Column(
                    [
                        ElevatedButton(
                            "Encode",
                            on_click=call_steg,
                        ),
                        
                    ]
                ),
                Column(
                    [
                        ElevatedButton(
                            "Decode",
                            on_click=call_unsteg,
                        ),
                    ]
                )
            ],
            alignment=flet.MainAxisAlignment.CENTER
        ),
    )


flet.app(target=main)
