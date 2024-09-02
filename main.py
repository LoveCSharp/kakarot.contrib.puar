# -*- coding: utf-8 -*-
import os
import base64
from datetime import datetime
import httpx
import flet as ft

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff")
question_type_map = {
    "SingleChoices": "单选",
    "MuitpleChoices": "多选",
    "Blanks": "填空",
}
paper_direction_map = {
    "左": "0",
    "上": "1",
    "右": "2",
    "下": "3",
}

def get_images_in_folder(folder_path):
    """
    获取文件夹下的所有图片的列表。
    参数：
    folder_path (str): 文件夹路径。
    返回:
    list: 包含所有图片文件的路径(完整路径)的列表。
    """
    images = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(IMAGE_EXTENSIONS):
            images.append(os.path.join(folder_path, filename))
    return images


def image_to_base64(image_path):
    """
    将图片文件转换为 Base64 编码字符串。
    参数:
    image_path (str): 图片文件的路径。
    返回:
    str: Base64 编码的字符串。
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


def main(page: ft.Page):
    page.title = "懒人答题卡阅卷 - 答题卡批量阅卷扩展程序"
    def on_upload_url_change(e: ft.ControlEvent):
        upload_url_text.value = f"{protocol_dropdown.value}://{host_text_field.value}:{port_text_field.value}/kakarot/api/exercise-result/upload-v2/exercise-{exercise_id_text_field.value}/clazz-{clazz_id_text_field.value}"
        page.update()

    protocol_dropdown = ft.Dropdown(
        label="协议",
        width=100,
        value="https",
        on_change=on_upload_url_change,
        options=[
            ft.dropdown.Option("https"),
            ft.dropdown.Option("http"),
        ],
    )
    host_text_field = ft.TextField(
        label="主机IP", value="127.0.0.1", on_change=on_upload_url_change, width=150
    )
    port_text_field = ft.TextField(
        label="端口", value="8289", on_change=on_upload_url_change, width=80
    )
    exercise_id_text_field = ft.TextField(
        label="习题ID", on_change=on_upload_url_change, value="1", width=80
    )
    clazz_id_text_field = ft.TextField(
        label="班级ID", on_change=on_upload_url_change, value="1", width=80
    )
    upload_url_text = ft.Text(
        f"{protocol_dropdown.value}://{host_text_field.value}:{port_text_field.value}/kakarot/api/exercise-result/upload-v2/exercise-{exercise_id_text_field.value}/clazz-{clazz_id_text_field.value}"
    )
    
    answer_sheet_regions_percent_max_text_field = ft.TextField(
        label="答题卡区域面积最大百分比", value="60", width=180
    )
    size_of_fill_area_text_field = ft.TextField(
        label="填涂区域大小(百分比)", value="40", width=150
    )
    paper_direction_dropdown = ft.Dropdown(
        label="答题卡朝向",
        width=100,
        value="左",
        options=[
            ft.dropdown.Option("左"),
            ft.dropdown.Option("上"),
            ft.dropdown.Option("右"),
            ft.dropdown.Option("下"),
        ],
    )
    erode_kernel_size_text_field = ft.TextField(
        label="腐蚀核大小（单位：像素）", value="4", width=180
    )
    dilate_kernel_size_text_field = ft.TextField(
        label="膨胀核大小（单位：像素）", value="4", width=180
    )

    text_answer_sheets_folder_path = ft.Text("请点击右侧按钮选择答题卡图像所在文件夹。")

    def on_file_picker_result(e: ft.FilePickerResultEvent):
        text_answer_sheets_folder_path.value = e.path
        button_upload.disabled = False
        page.update()

    file_picker = ft.FilePicker(
        on_result=on_file_picker_result,
    )
    page.overlay.append(file_picker)
    button_directory_get = ft.FilledButton(
        "点击选择",
        on_click=lambda _: file_picker.get_directory_path(),
    )

    grading_history_list_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=True,
            height=500,
        )
    async def on_upload_click(e: ft.ControlEvent):
        # 定义 Cookie 阅卷参数设置
        cookies = {
            'answer_sheet_regions_percent_max': answer_sheet_regions_percent_max_text_field.value,
            'size_of_fill_area': size_of_fill_area_text_field.value,
            'paper_direction': paper_direction_map[paper_direction_dropdown.value],
            'erode_kernel_size': erode_kernel_size_text_field.value,
            'dilate_kernel_size': dilate_kernel_size_text_field.value,
        }

        # 创建 headers 字典
        headers = {
            'Cookie': '; '.join([f'{k}={v}' for k, v in cookies.items()])
        }
        client = httpx.AsyncClient(verify=False, headers=headers)
        images = get_images_in_folder(text_answer_sheets_folder_path.value)
        for image in images:
            base64 = image_to_base64(image)
            try:
                r = await client.post(upload_url_text.value, json={"image": base64})
                if r.status_code == 200:
                    data = r.json()
                    unrecognized = []
                    # 单选、多选为空识别失败，当然这里的多选也有可能识别不全，无从判断
                    for q in ["SingleChoices", "MuitpleChoices"]:
                        if data["Result"][q]:
                            for i in range(len(data["Result"][q])):
                                if data["Result"][q][i] == "":
                                    unrecognized.append(f"{question_type_map[q]}({i+1})")
                    # 填空题为-1识别失败
                    q = "Blanks"
                    if data["Result"][q]:
                        for i in range(len(data["Result"][q])):
                            if data["Result"][q][i] == -1:
                                unrecognized.append(f"{question_type_map[q]}({i+1})")
                    if unrecognized:    # 未识别的情况存在
                        grading_history_list_view.controls.append(
                            ft.Text(
                                f"{datetime.now().strftime("%H:%M:%S")}:{data["Student"]["No"]}({data["Student"]["Name"]}): {','.join(unrecognized)}识别失败。",
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.YELLOW_700,
                                )
                            )
                    else:
                        grading_history_list_view.controls.append(
                            ft.Text(
                                f"{datetime.now().strftime("%H:%M:%S")}:{data["Student"]["No"]}({data["Student"]["Name"]})阅卷成功。",
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.GREEN_700,
                                )
                            )
                    grading_history_list_view.update()
                else:
                    data = r.json()
                    grading_history_list_view.controls.append(
                        ft.Text(
                            f"{datetime.now().strftime("%H:%M:%S")}:{data["error"]}",
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.RED_700,
                            )
                        )
                    grading_history_list_view.update()
            except Exception as e:
                grading_history_list_view.controls.append(
                        ft.Text(
                            f"{datetime.now().strftime("%H:%M:%S")}:{e}",
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.RED_700,
                            )
                        )
                grading_history_list_view.update()

    button_upload = ft.FilledButton(
        "上传阅卷",
        disabled=True,
        on_click=on_upload_click,
    )

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        protocol_dropdown,
                        host_text_field,
                        port_text_field,
                        exercise_id_text_field,
                        clazz_id_text_field,
                    ]
                ),
                ft.Row(
                    [
                        ft.Text("上传答题卡批阅地址："),
                        upload_url_text,
                    ]
                ),
                ft.Row(
                    [
                        answer_sheet_regions_percent_max_text_field,
                        size_of_fill_area_text_field,
                        paper_direction_dropdown,
                        erode_kernel_size_text_field,
                        dilate_kernel_size_text_field,
                    ],
                ),
                ft.Row(
                    [
                        ft.Text("答题卡所在文件夹："),
                        text_answer_sheets_folder_path,
                        button_directory_get,
                        button_upload,
                    ]
                ),
                ft.Row(
                    [
                        grading_history_list_view,
                    ],
                ),
                
            ]
        )
    )

ft.app(main)
