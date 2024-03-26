# Copyright 2023 osiworx

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You
# may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

# you could set this in your env as ENV Variables, to be able to just run we do it like this


import gradio as gr
import model_list
import os
from generators.civitai.client import civitai_client
from generators.hordeai.client import hordeai_client
from generators.hordeai.client import hordeai_models
from horde_sdk import ANON_API_KEY
from settings import io

settings_io = io.settings_io()
settings_data = settings_io.load_settings()

hordeai_model_list = hordeai_models().read_model_list()

host = 'localhost'
mongo_host = 'localhost'

if os.getenv("QDRANT_HOST") is not None:
    host = os.getenv("QDRANT_HOST")

if os.getenv("MONGO_HOST") is not None:
    mongo_host = os.getenv("MONGO_HOST")

os.environ['COLLECTION_DB_URI'] = f'mongodb://{mongo_host}:27017/'
os.environ["USER_MANAGED_QDRANT_HOST"] = host
os.environ["USER_MANAGED_QDRANT_PORT"] = "6333"

from llmware.gguf_configs import GGUFConfigs

GGUFConfigs().set_config("n_gpu_layers", 50)

import llm_interface_qdrant

interface = llm_interface_qdrant.LLM_INTERFACE()


def set_llm_settings(model, temperature, n_ctx, n_gpu_layers, max_tokens, top_k, instruct):
    settings_data['LLM Model'] = model
    settings_data['Temperature'] = temperature
    settings_data['max output Tokens'] = max_tokens
    settings_data['top_k'] = top_k
    settings_data['Instruct Model'] = instruct
    settings_io.write_settings(settings_data)


def set_civitai_settings(air, steps, cfg, width, heigth, clipskip):
    settings_data['civitai_Air'] = air
    settings_data['civitai_Steps'] = steps
    settings_data['civitai_CFG Scale'] = cfg
    settings_data['civitai_Width'] = width
    settings_data['civitai_Height'] = heigth
    settings_data['civitai_Clipskip'] = clipskip
    settings_io.write_settings(settings_data)


def set_hordeai_settings(api_key, model, sampler, steps, cfg, width, heigth, clipskip):
    settings_data['horde_api_key'] = api_key
    settings_data['horde_Model'] = model
    settings_data['horde_Sampler'] = sampler
    settings_data['horde_Steps'] = steps
    settings_data['horde_CFG Scale'] = cfg
    settings_data['horde_Width'] = width
    settings_data['horde_Height'] = heigth
    settings_data['horde_Clipskip'] = clipskip
    settings_io.write_settings(settings_data)


def set_model(model, temperature, max_tokens, gpu_layer, top_k, instruct):
    set_llm_settings(model, temperature, max_tokens, top_k, instruct)
    return interface.change_model(model, temperature, max_tokens, gpu_layer, top_k, instruct)


def civitai_get_last_prompt():
    return interface.last_prompt, interface.last_negative_prompt, settings_data['civitai_Air'], settings_data[
        'civitai_Steps'], settings_data['civitai_CFG Scale'], settings_data['civitai_Width'], settings_data[
        'civitai_Height'], settings_data['civitai_Clipskip']


def hordeai_get_last_prompt():
    return interface.last_prompt, interface.last_negative_prompt, settings_data['horde_api_key'], settings_data[
        'horde_Model'], settings_data['horde_Sampler'], settings_data['horde_Steps'], settings_data['horde_CFG Scale'], \
    settings_data['horde_Width'], settings_data['horde_Height'], settings_data['horde_Clipskip']


def run_civitai_generation(air, prompt, negative_prompt, steps, cfg, width, heigth, clipskip):
    set_civitai_settings(air, steps, cfg, width, heigth, clipskip)
    client = civitai_client()
    return client.request_generation(air, prompt, negative_prompt, steps, cfg, width, heigth, clipskip)


def run_hordeai_generation(api_key, prompt, negative_prompt, model, sampler, steps, cfg, width, heigth, clipskip):
    set_hordeai_settings(api_key, model, sampler, steps, cfg, width, heigth, clipskip)
    client = hordeai_client()
    return client.request_generation(api_key=api_key, prompt=prompt, negative_prompt=negative_prompt,
                                     sampler=sampler, model=model, steps=steps, cfg=cfg, width=width, heigth=heigth,
                                     clipskip=clipskip)


def get_last_prompt():
    return interface.last_prompt, interface.last_negative_prompt


def llm_get_settings():
    return settings_data["LLM Model"], settings_data['Temperature'], settings_data['GPU Layers'], settings_data[
        'max output Tokens'], settings_data['top_k'], settings_data['Instruct Model']


def get_prompt_template():
    interface.prompt_template = settings_data["prompt_templates"][settings_data["selected_template"]]
    return settings_data["prompt_templates"][settings_data["selected_template"]]["blurb1"]


def set_prompt_template_select(value):
    settings_data['selected_template'] = value
    settings_io.write_settings(settings_data)
    return settings_data["prompt_templates"][value]


def set_prompt_template(selection, prompt_text):
    return_data = interface.set_prompt(prompt_text)
    settings_data["prompt_templates"][selection]["blurb1"] = prompt_text
    settings_io.write_settings(settings_data)
    return return_data


css = """
.gr-image {
  min-width: 60px !important;
  max-width: 60px !important;
  min-heigth: 65px !important;
  max-heigth: 65px !important;  
  
}
.app-title {
  font-size: 50px;
}
"""

civitai_prompt_input = gr.TextArea(interface.last_prompt, lines=10, label="Prompt")
civitai_negative_prompt_input = gr.TextArea(interface.last_negative_prompt, lines=5, label="Negative Prompt")
hordeai_prompt_input = gr.TextArea(interface.last_prompt, lines=10, label="Prompt")
hordeai_negative_prompt_input = gr.TextArea(interface.last_negative_prompt, lines=5, label="Negative Prompt")

LLM = gr.Dropdown(
    model_list.model_list.keys(), value=settings_data['LLM Model'], label="LLM Model",
    info="Will add more LLMs later!"
)
Temperature = gr.Slider(0, 1, step=0.1, value=settings_data['Temperature'], label="Temperature",
                        info="Choose between 0 and 1")
max = gr.Slider(0, 1024, step=1, value=settings_data['Context Length'], label="max output Tokens",
                info="Choose between 1 and 1024")
GPU = gr.Slider(0, 1024, step=1, value=settings_data['GPU Layers'], label="GPU Layers",
                info="Choose between 1 and 1024")
top_k = gr.Slider(0, 50, step=1, value=settings_data['top_k'],
                  label="how many entrys to be fetched from the vector store",
                  info="Choose between 1 and 50 be careful not to overload the context window of the LLM")
Instruct = gr.Checkbox(label='Instruct Model', value=settings_data['Instruct Model'])

civitai_Air = gr.TextArea(lines=1, label="Air", value=settings_data['civitai_Air'])
civitai_Steps = gr.Slider(0, 100, step=1, value=settings_data['civitai_Steps'], label="Steps",
                          info="Choose between 1 and 100")
civitai_CFG = gr.Slider(0, 20, step=0.1, value=settings_data['civitai_CFG Scale'], label="CFG Scale",
                        info="Choose between 1 and 20")
civitai_Width = gr.Slider(0, 1024, step=1, value=settings_data['civitai_Width'], label="Width",
                          info="Choose between 1 and 1024")
civitai_Height = gr.Slider(0, 1024, step=1, value=settings_data['civitai_Height'], label="Height",
                           info="Choose between 1 and 1024")
civitai_Clipskip = gr.Slider(0, 10, step=1, value=settings_data['civitai_Clipskip'], label="Clipskip",
                             info="Choose between 1 and 10")

horde_api_key = gr.TextArea(lines=1, label="API Key", value=settings_data['horde_api_key'], type='password')
hordeai_Model = gr.Dropdown(choices=hordeai_model_list.keys(), value='Deliberate 3.0', label='Model')
hordeai_Sampler = gr.Dropdown(choices=["k_dpmpp_2s_a", "k_lms", "k_heun", "k_heun", "k_euler", "k_euler_a",
                                       "k_dpm_2", "k_dpm_2_a", "k_dpm_fast", "k_dpm_adaptive", "k_dpmpp_2s_a",
                                       "k_dpmpp_2m", "dpmsolver", "k_dpmpp_sde", "lcm", "DDIM"
                                       ], value=settings_data['horde_Sampler'], label='Sampler')

hordeai_Steps = gr.Slider(0, 100, step=1, value=settings_data['horde_Steps'], label="Steps",
                          info="Choose between 1 and 100")
hordeai_CFG = gr.Slider(0, 20, step=0.1, value=settings_data['horde_CFG Scale'], label="CFG Scale",
                        info="Choose between 1 and 20")
hordeai_Width = gr.Slider(0, 1024, step=1, value=settings_data['horde_Width'], label="Width",
                          info="Choose between 1 and 1024")
hordeai_Height = gr.Slider(0, 1024, step=1, value=settings_data['horde_Height'], label="Height",
                           info="Choose between 1 and 1024")
hordeai_Clipskip = gr.Slider(0, 10, step=1, value=settings_data['horde_Clipskip'], label="Clipskip",
                             info="Choose between 1 and 10")

prompt_template = gr.TextArea(settings_data["prompt_templates"][settings_data["selected_template"]]["blurb1"], lines=20)
prompt_template_select = gr.Dropdown(choices=settings_data["prompt_templates"].keys(),
                                     value=settings_data["selected_template"], label='Template', interactive=True)

with gr.Blocks(css=css) as pq_ui:
    with gr.Row():
        # Image element (adjust width as needed)
        gr.Image(os.path.join(os.getcwd(), "logo/pq_v_small.jpg"), width="20vw", show_label=False,
                 show_download_button=False, container=False, elem_classes="gr-image", )

        # Title element (adjust font size and styling with CSS if needed)
        gr.Markdown("**Prompt Quill**", elem_classes="app-title")  # Add unique ID for potential CSS styling

    with gr.Tab("Chat"):
        gr.ChatInterface(
            interface.run_llm_response,
            chatbot=gr.Chatbot(height=500, render=False, elem_id="chatbot"),
            textbox=gr.Textbox(placeholder="Enter your prompt to work with",
                               container=False,
                               scale=7,
                               render=False,  # render is false as we are in a blocks environment
                               ),
            theme="soft",
            examples=['A fishermans lake', 'night at cyberpunk city', 'living in a steampunk world'],
            cache_examples=True,
            retry_btn="🔄  Retry",
            undo_btn="↩️ Undo",
            clear_btn="Clear"
        )

    with gr.Tab("Character") as Character:
        gr.on(
            triggers=[Character.select],
            fn=get_prompt_template,
            inputs=None,
            outputs=[prompt_template]
        )
        gr.on(
            triggers=[prompt_template_select.select],
            fn=set_prompt_template_select,
            inputs=prompt_template_select,
            outputs=[prompt_template
                     ]
        )
        gr.Interface(
            set_prompt_template,
            [prompt_template_select, prompt_template, ],
            outputs=None,
            allow_flagging='never',
            flagging_options=None,
        )

    with gr.Tab("Model Settings") as llm_settings:
        gr.on(
            triggers=[llm_settings.select],
            fn=llm_get_settings,
            inputs=None,
            outputs=[LLM,
                     Temperature,
                     GPU,
                     max,
                     top_k,
                     Instruct
                     ]
        )
        gr.Interface(
            set_model,
            [
                LLM,
                Temperature,
                max,
                GPU,
                top_k,
                Instruct
            ]
            , outputs="text",
            allow_flagging='never',
            flagging_options=None

        )
    with gr.Tab("Generator") as generator:
        gr.on(
            triggers=[generator.select],
            fn=civitai_get_last_prompt,
            inputs=None,
            outputs=[civitai_prompt_input,
                     civitai_negative_prompt_input,
                     civitai_Air,
                     civitai_Steps,
                     civitai_CFG,
                     civitai_Width,
                     civitai_Height,
                     civitai_Clipskip
                     ]
        )
        with gr.Tab("Civitai") as civitai:
            gr.Interface(
                run_civitai_generation,
                [
                    civitai_Air,
                    civitai_prompt_input,
                    civitai_negative_prompt_input,
                    civitai_Steps,
                    civitai_CFG,
                    civitai_Width,
                    civitai_Height,
                    civitai_Clipskip,

                ]
                , outputs=gr.Image(label="Generated Image"),  # "text",
                allow_flagging='never',
                flagging_options=None,
                # live=True
            )
        with gr.Tab("HordeAI") as hordeai:
            gr.on(
                triggers=[hordeai.select],
                fn=hordeai_get_last_prompt,
                inputs=None,
                outputs=[hordeai_prompt_input,
                         hordeai_negative_prompt_input,
                         horde_api_key,
                         hordeai_Model,
                         hordeai_Sampler,
                         hordeai_Steps,
                         hordeai_CFG,
                         hordeai_Width,
                         hordeai_Height,
                         hordeai_Clipskip]
            )
            gr.Interface(
                run_hordeai_generation,
                [
                    horde_api_key,
                    hordeai_prompt_input,
                    hordeai_negative_prompt_input,
                    hordeai_Model,
                    hordeai_Sampler,
                    hordeai_Steps,
                    hordeai_CFG,
                    hordeai_Width,
                    hordeai_Height,
                    hordeai_Clipskip
                ]
                , outputs=gr.Image(label="Generated Image"),  # "text",
                allow_flagging='never',
                flagging_options=None,
                # live=True
            )
if __name__ == "__main__":
    pq_ui.launch(inbrowser=True)  # share=True
