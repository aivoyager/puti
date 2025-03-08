"""
@Author: obstacle
@Time: 21/01/25 11:22
@Description:  
"""
import io
import os
import uuid
import websocket
import json
import requests
import urllib.request
import urllib.parse

from PIL import Image
from logs import logger_factory

lgr = logger_factory.default


def open_websocket_connection():
    client_id = str(uuid.uuid4())
    # TODO: conf fix
    server_address = f"98.80.144.31:9000"
    lgr.info(f"Opening websocket connection to {server_address}")
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
    return ws, server_address, client_id


def queue_prompt(prompt, client_id, server_address):
    p = {"prompt": prompt, "client_id": client_id}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(p).encode('utf-8')
    result = requests.post(f"http://{server_address}/prompt", data=data, headers=headers)
    # result = requests.post(f"https://toto.memeta.io/prompt", data=data, headers=headers)
    if result.status_code == 200:
        return result.json()


def track_progress(prompt, ws, prompt_id):
    node_ids = list(prompt.keys())
    finished_nodes = []

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'progress':
                data = message['data']
                current_step = data['value']
                print('In K-Sampler -> Step: ', current_step, ' of: ', data['max'])
            if message['type'] == 'execution_cached':
                data = message['data']
                for itm in data['nodes']:
                    if itm not in finished_nodes:
                        finished_nodes.append(itm)
                        print('Progess: ', len(finished_nodes), '/', len(node_ids), ' Tasks done')
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] not in finished_nodes:
                    finished_nodes.append(data['node'])
                    print('Progess: ', len(finished_nodes), '/', len(node_ids), ' Tasks done')

                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
        else:
            continue  # previews are binary data
    return


def get_history(prompt_id, server_address):
    response = requests.get(f"http://{server_address}/history/{prompt_id}")
    if response.status_code == 200:
        return response.json()


def get_image(filename, subfolder, folder_type, server_address):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    result = requests.get(f"http://{server_address}/view?{url_values}")
    if result.status_code == 200:
        return result.content


def get_images(prompt_id, server_address, allow_preview=False):
    output_images = []

    history = get_history(prompt_id, server_address)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        output_data = {}
        if 'images' in node_output:
            for image in node_output['images']:
                if allow_preview and image['type'] == 'temp':
                    preview_data = get_image(image['filename'], image['subfolder'], image['type'], server_address)
                    output_data['image_data'] = preview_data
                if image['type'] == 'output':
                    image_data = get_image(image['filename'], image['subfolder'], image['type'], server_address)
                    output_data['image_data'] = image_data
        output_data['file_name'] = image['filename']
        output_data['type'] = image['type']
        output_images.append(output_data)

    return output_images


def save_image(images, output_path, save_previews) -> str:
    for itm in images:
        directory = os.path.join(output_path, 'temp/') if itm['type'] == 'temp' and save_previews else output_path
        os.makedirs(directory, exist_ok=True)
        try:
            image = Image.open(io.BytesIO(itm['image_data']))
            file_name = os.path.join(directory, itm['file_name'])
            image.save(file_name)
            return file_name
        except Exception as e:
            lgr.error(f"Failed to save image {itm['file_name']}: {e}")


def generate_image_by_prompt(prompt, output_path, save_previews=False):
    try:
        ws, server_address, client_id = open_websocket_connection()
        prompt_id = queue_prompt(prompt, client_id, server_address)['prompt_id']
        track_progress(prompt, ws, prompt_id)
        images = get_images(prompt_id, server_address, save_previews)
        path = save_image(images, output_path, save_previews)
        return path
    except Exception as e:
        print(e)
        return ""
    finally:
        ws.close()
