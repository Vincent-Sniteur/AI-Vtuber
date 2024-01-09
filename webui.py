from nicegui import ui, app
import sys, os, json, subprocess, importlib, re, threading, signal
import logging, traceback
import time
import asyncio
# from functools import partial

import http.server
import socketserver

from utils.config import Config
from utils.common import Common
from utils.logger import Configure_logger
from utils.audio import Audio

"""
Global Variables
"""
# Create a global variable to indicate whether the program is running
running_flag = False

# Create a subprocess object to store the running external program
running_process = None

common = None
config = None
audio = None
my_handle = None
config_path = None

web_server_port = 12345

"""
Initialize Basic Configuration
"""
def init():
    global config_path, config, common, audio

    common = Common()

    if getattr(sys, 'frozen', False):
        # This is an executable file
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
        file_relative_path = os.path.dirname(os.path.abspath(bundle_dir))
    else:
        # This is the source code
        file_relative_path = os.path.dirname(os.path.abspath(__file__))

    # logging.info(file_relative_path)

    # Initialize folders
    def init_dir():
        # Create a log folder
        log_dir = os.path.join(file_relative_path, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create an audio output folder
        audio_out_dir = os.path.join(file_relative_path, 'out')
        if not os.path.exists(audio_out_dir):
            os.makedirs(audio_out_dir)
            
    init_dir()

    # Configuration file path
    config_path = os.path.join(file_relative_path, 'config.json')

    audio = Audio(config_path, 2)

    # Log file path
    file_path = "./log/log-" + common.get_bj_time(1) + ".txt"
    Configure_logger(file_path)

    # Get the logger for the httpx library
    httpx_logger = logging.getLogger("httpx")
    # Set the httpx logger level to WARNING
    httpx_logger.setLevel(logging.WARNING)

    # Get the logger for a specific library
    watchfiles_logger = logging.getLogger("watchfiles")
    # Set the log level to WARNING or higher to suppress INFO level log messages
    watchfiles_logger.setLevel(logging.WARNING)

    logging.debug("Configuration file path=" + str(config_path))

    # Instantiate the Config class
    config = Config(config_path)

init()

# Dark mode
dark = ui.dark_mode()

"""
Common Functions
"""
def textarea_data_change(data):
    """
    Convert string array data format
    """
    tmp_str = ""
    for tmp in data:
        tmp_str = tmp_str + tmp + "\n"
    
    return tmp_str

# Web service thread
async def web_server_thread(web_server_port):
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", web_server_port), Handler) as httpd:
        logging.info(f"Web server is running on port: {web_server_port}")
        logging.info(f"You can directly access the Live2D page at http://127.0.0.1:{web_server_port}/Live2D/")
        httpd.serve_forever()

"""
Web UI
"""
# Configuration
webui_ip = config.get("webui", "ip")
webui_port = config.get("webui", "port")
webui_title = config.get("webui", "title")

# CSS
theme_choose = config.get("webui", "theme", "choose")
tab_panel_css = config.get("webui", "theme", "list", theme_choose, "tab_panel")
card_css = config.get("webui", "theme", "list", theme_choose, "card")
button_bottom_css = config.get("webui", "theme", "list", theme_choose, "button_bottom")
button_bottom_color = config.get("webui", "theme", "list", theme_choose, "button_bottom_color")
button_internal_css = config.get("webui", "theme", "list", theme_choose, "button_internal")
button_internal_color = config.get("webui", "theme", "list", theme_choose, "button_internal_color")
switch_internal_css = config.get("webui", "theme", "list", theme_choose, "switch_internal")

def goto_func_page():
    """
    Go to the functional page
    """
    global audio

    """
    Button call functions
    """
    # Create a function to run an external program
    def run_external_program(config_path="config.json", type="webui"):
        global running_flag, running_process

        if running_flag:
            if type == "webui":
                ui.notify(position="top", type="warning", message="Already running, please do not run again.")
            return

        try:
            running_flag = True

            # Specify the program and parameters to run here
            # For example, run a Python script named "bilibili.py"
            running_process = subprocess.Popen(["python", f"{select_platform.value}.py"])

            if type == "webui":
                ui.notify(position="top", type="positive", message="Program has started running.")
            logging.info("Program has started running")

            return {"code": 200, "msg": "Program has started running"}
        except Exception as e:
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"Error: {e}")
            logging.error(traceback.format_exc())
            running_flag = False

            return {"code": -1, "msg": f"Failed to run! {e}"}


    # Define a function to stop the running program
    def stop_external_program(type="webui"):
        global running_flag, running_process

        if running_flag:
            try:
                running_process.terminate()  # Terminate the subprocess
                running_flag = False
                if type == "webui":
                    ui.notify(position="top", type="positive", message="Program has been stopped.")
                logging.info("Program has been stopped")
            except Exception as e:
                if type == "webui":
                    ui.notify(position="top", type="negative", message=f"Stop error: {e}")
                logging.error(f"Stop error: {e}")

                return {"code": -1, "msg": f"Failed to restart! {e}"}


    # Turn off the light
    def change_light_status(type="webui"):
        if dark.value:
            button_light.set_text("Turn Off")
        else:
            button_light.set_text("Turn On")
        dark.toggle()

    # Restart
    def restart_application(type="webui"):
        try:
            # Stop running first
            stop_external_program(type)

            logging.info(f"Restarting webui")
            if type == "webui":
                ui.notify(position="top", type="ongoing", message=f"Restarting...")
            python = sys.executable
            os.execl(python, python, *sys.argv)  # Start a new instance of the application
        except Exception as e:
            logging.error(traceback.format_exc())
            return {"code": -1, "msg": f"Restart failed! {e}"}
        
    # Restore factory settings
    def factory(src_path='config.json.bak', dst_path='config.json', type="webui"):
        try:
            with open(src_path, 'r', encoding="utf-8") as source:
                with open(dst_path, 'w', encoding="utf-8") as destination:
                    destination.write(source.read())
            logging.info("Factory settings restored successfully!")
            if type == "webui":
                ui.notify(position="top", type="positive", message=f"Factory settings restored successfully!")
            
            # Restart
            restart_application()

            return {"code": 200, "msg": "Factory settings restored successfully!"}
        except Exception as e:
            logging.error(f"Failed to restore factory settings!\n{e}")
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"Failed to restore factory settings!\n{e}")
            
            return {"code": -1, "msg": f"Failed to restore factory settings!\n{e}"}
        
            # openai 测试key可用性
    def test_openai_key():
        # import openai
        # from packaging import version

        # # 检查可用性
        # def check_useful(base_url, api_keys):
        #     # 尝试调用 list engines 接口
        #     try:
        #         api_key = api_keys.split('\n')[0].rstrip()

        #         logging.info(f"base_url=【{base_url}】, api_keys=【{api_key}】")

        #         # openai.base_url = self.data_openai['api']
        #         # openai.api_key = self.data_openai['api_key'][0]

        #         logging.debug(f"openai.__version__={openai.__version__}")

        #         openai.api_base = base_url
        #         openai.api_key = api_key

        #         # 判断openai库版本，1.x.x和0.x.x有破坏性更新
        #         if version.parse(openai.__version__) < version.parse('1.0.0'):
        #             # 调用 ChatGPT 接口生成回复消息
        #             resp = openai.ChatCompletion.create(
        #                 model=select_openai_tts_model.value,
        #                 messages=[{"role": "user", "content": "Hi"}],
        #                 timeout=30
        #             )
        #         else:
        #             client = openai.OpenAI(base_url=openai.api_base, api_key=openai.api_key)
        #             # 调用 ChatGPT 接口生成回复消息
        #             resp = client.chat.completions.create(
        #                 model=select_openai_tts_model.value,
        #                 messages=[{"role": "user", "content": "Hi"}],
        #                 timeout=30
        #             )

        #         logging.debug(resp)
        #         logging.info("OpenAI API key 可用")

        #         return True
        #     except openai.OpenAIError as e:
        #         logging.error(f"OpenAI API key 不可用: {e}")
        #         return False
        
        # if check_useful(input_openai_api.value, textarea_openai_api_key.value):
        #     ui.notify(position="top", type="positive", message=f"测试通过！")
        # else:
        #     ui.notify(position="top", type="negative", message=f"测试失败！")

        if common.test_openai_key(input_openai_api.value, textarea_openai_api_key.value, select_openai_tts_model.value):
            ui.notify(position="top", type="positive", message=f"测试通过！")
        else:
            ui.notify(position="top", type="negative", message=f"测试失败！")
    
    """
    API
    """
    from starlette.requests import Request

    """
    System commands
        type: command type (run/stop/restart/factory)
        data 传入的json

    data_json = {
        "type": "command_name",
        "data": {
            "key": "value"
        }
    }

    return:
        {"code": 200, "msg": "Success"}
        {"code": -1, "msg": "Failure"}
    """
    @app.post('/sys_cmd')
    async def sys_cmd(request: Request):
        try:
            data_json = await request.json()
            logging.info(f'Received data: {data_json}')
            logging.info(f"Executing {data_json['type']}命令...")

            resp_json = {}

            if data_json['type'] == 'run':
                """
                {
                    "type": "run",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # Run
                resp_json = run_external_program(data_json['data']['config_path'], type="api")
            elif data_json['type'] =='stop':
                """
                {
                    "type": "stop",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # Stop
                resp_json = stop_external_program(type="api")
            elif data_json['type'] =='restart':
                """
                {
                    "type": "restart",
                    "api_type": "webui",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # Restart
                resp_json = restart_application(type=data_json['api_type'])
            elif data_json['type'] =='factory':
                """
                {
                    "type": "factory",
                    "api_type": "webui",
                    "data": {
                        "src_path": "config.json.bak",
                        "dst_path": "config.json"
                    }
                }
                """
                # Restore factory settings
                resp_json = factory(data_json['data']['src_path'], data_json['data']['dst_path'], type="api")

            return resp_json
        except Exception as e:
            logging.error(traceback.format_exc())
            return {"code": -1, "msg": f"{data_json['type']} execution failed! {e}"}

    """
    Text page
    """
    # Text page - Add
    def copywriting_add():
        data_len = len(copywriting_config_var)
        tmp_config = {
            "file_path": f"data/copywriting{int(data_len / 5) + 1}/",
            "audio_path": f"out/copywriting{int(data_len / 5) + 1}/",
            "continuous_play_num": 2,
            "max_play_time": 10.0,
            "play_list": []
        }

        with copywriting_config_card.style(card_css):
            with ui.row():
                copywriting_config_var[str(data_len)] = ui.input(label=f"Copywriting storage path#{int(data_len / 5) + 1}", value=tmp_config["file_path"], placeholder='Copywriting file storage path. Not recommended to change.').style("width:200px;")
                copywriting_config_var[str(data_len + 1)] = ui.input(label=f"Audio storage path#{int(data_len / 5) + 1}", value=tmp_config["audio_path"], placeholder='Copywriting audio file storage path. Not recommended to change.').style("width:200px;")
                copywriting_config_var[str(data_len + 2)] = ui.input(label=f"Continuous play count#{int(data_len / 5) + 1}", value=tmp_config["continuous_play_num"], placeholder='Number of audio files to play continuously in the copywriting playlist. If exceeded, switch to the next copywriting list.').style("width:200px;")
                copywriting_config_var[str(data_len + 3)] = ui.input(label=f"Continuous play time#{int(data_len / 5) + 1}", value=tmp_config["max_play_time"], placeholder='Duration of continuous play of audio in the copywriting playlist. If exceeded, switch to the next copywriting list.').style("width:200px;")
                copywriting_config_var[str(data_len + 4)] = ui.textarea(label=f"Playlist#{int(data_len / 5) + 1}", value=textarea_data_change(tmp_config["play_list"]), placeholder='Enter the full name of the audio file to be played here. After filling in, click Save Configuration. Copy the full name from the audio list, separated by line breaks. Do not fill in randomly.').style("width:500px;")

    # Text page - Delete
    def copywriting_del(index):
        try:
            copywriting_config_card.remove(int(index) - 1)
            # Delete operation
            keys_to_delete = [str(5 * (int(index) - 1) + i) for i in range(5)]
            for key in keys_to_delete:
                if key in copywriting_config_var:
                    del copywriting_config_var[key]

            # Re-number the remaining keys
            updates = {}
            for key in sorted(copywriting_config_var.keys(), key=int):
                new_key = str(int(key) - 5 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = copywriting_config_var[key]

            # Apply updates
            copywriting_config_var.clear()
            copywriting_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"Error, index value configuration is incorrect: {e}")
            logging.error(traceback.format_exc())


    # Text page - Loop play
    def copywriting_loop_play():
        if running_flag != 1:
            ui.notify(position="top", type="warning", message=f"Please click 'One-click Run' first, and then play.")
            return
        
        logging.info("Start looping play copywriting~")
        ui.notify(position="top", type="positive", message="Start looping play copywriting~")
        
        audio.unpause_copywriting_play()

    # Text page - Pause play
    def copywriting_pause_play():
        if running_flag != 1:
            ui.notify(position="top", type="warning", message=f"Please click 'One-click Run' first, and then play.")
            return
        
        audio.pause_copywriting_play()
        logging.info("Copywriting paused~")
        ui.notify(position="top", type="positive", message="Copywriting paused~")

    """
    Configuration Operations
    """
    # Configuration check
    def check_config():
        # Common configuration page
        if select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'cookie' and input_bilibili_cookie.value == '':
            ui.notify(position="top", type="warning", message="Please go to General Configuration-Bilibili and fill in Bilibili cookie.")
            return False
        elif select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'open_live' and \
            (input_bilibili_open_live_ACCESS_KEY_ID.value == '' or input_bilibili_open_live_ACCESS_KEY_SECRET.value == '' or \
            input_bilibili_open_live_APP_ID.value == '' or input_bilibili_open_live_ROOM_OWNER_AUTH_CODE.value == ''):
            ui.notify(position="top", type="warning", message="Please go to General Configuration-Bilibili and fill in open platform configuration.")
            return False

        return True

    # Save configuration
    def save_config():
        global config, config_path

        # Configuration check
        if not check_config():
            return

        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logging.error(f"Unable to read the configuration file!\n{e}")
            ui.notify(position="top", type="negative", message=f"Unable to read the configuration file! {e}")
            return False

        def common_textarea_handle(content):
            """Common textEdit - Multiline text content processing

            Args:
                content (str): Original multiline text content

            Returns:
                _type_: Processed multiline text content
            """
            # Common multiline separators
            separators = [" ", "\n"]

            ret = [token.strip() for separator in separators for part in content.split(separator) if (token := part.strip())]
            if 0 != len(ret):
                ret = ret[1:]

            return ret


        try:
            """
            General Configuration
            """
            if True:
                config_data["platform"] = select_platform.value
                config_data["room_display_id"] = input_room_display_id.value
                config_data["chat_type"] = select_chat_type.value
                config_data["visual_body"] = select_visual_body.value
                config_data["need_lang"] = select_need_lang.value
                config_data["before_prompt"] = input_before_prompt.value
                config_data["after_prompt"] = input_after_prompt.value
                config_data["audio_synthesis_type"] = select_audio_synthesis_type.value

                # Bilibili
                config_data["bilibili"]["login_type"] = select_bilibili_login_type.value
                config_data["bilibili"]["cookie"] = input_bilibili_cookie.value
                config_data["bilibili"]["ac_time_value"] = input_bilibili_ac_time_value.value
                config_data["bilibili"]["username"] = input_bilibili_username.value
                config_data["bilibili"]["password"] = input_bilibili_password.value
                config_data["bilibili"]["open_live"]["ACCESS_KEY_ID"] = input_bilibili_open_live_ACCESS_KEY_ID.value
                config_data["bilibili"]["open_live"]["ACCESS_KEY_SECRET"] = input_bilibili_open_live_ACCESS_KEY_SECRET.value
                config_data["bilibili"]["open_live"]["APP_ID"] = int(input_bilibili_open_live_APP_ID.value)
                config_data["bilibili"]["open_live"]["ROOM_OWNER_AUTH_CODE"] = input_bilibili_open_live_ROOM_OWNER_AUTH_CODE.value

                # twitch
                config_data["twitch"]["token"] = input_twitch_token.value
                config_data["twitch"]["user"] = input_twitch_user.value
                config_data["twitch"]["proxy_server"] = input_twitch_proxy_server.value
                config_data["twitch"]["proxy_port"] = input_twitch_proxy_port.value

                # Audio playback
                config_data["play_audio"]["enable"] = switch_play_audio_enable.value
                config_data["play_audio"]["text_split_enable"] = switch_play_audio_text_split_enable.value
                config_data["play_audio"]["normal_interval"] = round(float(input_play_audio_normal_interval.value), 2)
                config_data["play_audio"]["out_path"] = input_play_audio_out_path.value
                config_data["play_audio"]["player"] = select_play_audio_player.value

                # Audio_player
                config_data["audio_player"]["api_ip_port"] = input_audio_player_api_ip_port.value

                # Read comments
                config_data["read_comment"]["enable"] = switch_read_comment_enable.value
                config_data["read_comment"]["read_username_enable"] = switch_read_comment_read_username_enable.value
                config_data["read_comment"]["username_max_len"] = int(input_read_comment_username_max_len.value)
                config_data["read_comment"]["voice_change"] = switch_read_comment_voice_change.value
                config_data["read_comment"]["read_username_copywriting"] = common_textarea_handle(textarea_read_comment_read_username_copywriting.value)

                # Read username when replying
                config_data["read_user_name"]["enable"] = switch_read_user_name_enable.value
                config_data["read_user_name"]["username_max_len"] = int(input_read_user_name_username_max_len.value)
                config_data["read_user_name"]["voice_change"] = switch_read_user_name_voice_change.value
                config_data["read_user_name"]["reply_before"] = common_textarea_handle(textarea_read_user_name_reply_before.value)
                config_data["read_user_name"]["reply_after"] = common_textarea_handle(textarea_read_user_name_reply_after.value)

                # Logging
                config_data["comment_log_type"] = select_comment_log_type.value
                config_data["captions"]["enable"] = switch_captions_enable.value
                config_data["captions"]["file_path"] = input_captions_file_path.value

                # Local Q&A
                config_data["local_qa"]["text"]["enable"] = switch_local_qa_text_enable.value
                local_qa_text_type = select_local_qa_text_type.value
                if local_qa_text_type == "自定义json":
                    config_data["local_qa"]["text"]["type"] = "json"
                elif local_qa_text_type == "一问一答":
                    config_data["local_qa"]["text"]["type"] = "text"
                config_data["local_qa"]["text"]["file_path"] = input_local_qa_text_file_path.value
                config_data["local_qa"]["text"]["similarity"] = round(float(input_local_qa_text_similarity.value), 2)
                config_data["local_qa"]["audio"]["enable"] = switch_local_qa_audio_enable.value
                config_data["local_qa"]["audio"]["file_path"] = input_local_qa_audio_file_path.value
                config_data["local_qa"]["audio"]["similarity"] = round(float(input_local_qa_audio_similarity.value), 2)
            
                # Filtering
                config_data["filter"]["before_must_str"] = common_textarea_handle(textarea_filter_before_must_str.value)
                config_data["filter"]["after_must_str"] = common_textarea_handle(textarea_filter_after_must_str.value)
                config_data["filter"]["before_filter_str"] = common_textarea_handle(textarea_filter_before_filter_str.value)
                config_data["filter"]["after_filter_str"] = common_textarea_handle(textarea_filter_after_filter_str.value)
                config_data["filter"]["badwords_path"] = input_filter_badwords_path.value
                config_data["filter"]["bad_pinyin_path"] = input_filter_bad_pinyin_path.value
                config_data["filter"]["max_len"] = int(input_filter_max_len.value)
                config_data["filter"]["max_char_len"] = int(input_filter_max_char_len.value)
                config_data["filter"]["comment_forget_duration"] = round(float(input_filter_comment_forget_duration.value), 2)
                config_data["filter"]["comment_forget_reserve_num"] = int(input_filter_comment_forget_reserve_num.value)
                config_data["filter"]["gift_forget_duration"] = round(float(input_filter_gift_forget_duration.value), 2)
                config_data["filter"]["gift_forget_reserve_num"] = int(input_filter_gift_forget_reserve_num.value)
                config_data["filter"]["entrance_forget_duration"] = round(float(input_filter_entrance_forget_duration.value), 2)
                config_data["filter"]["entrance_forget_reserve_num"] = int(input_filter_entrance_forget_reserve_num.value)
                config_data["filter"]["follow_forget_duration"] = round(float(input_filter_follow_forget_duration.value), 2)
                config_data["filter"]["follow_forget_reserve_num"] = int(input_filter_follow_forget_reserve_num.value)
                config_data["filter"]["talk_forget_duration"] = round(float(input_filter_talk_forget_duration.value), 2)
                config_data["filter"]["talk_forget_reserve_num"] = int(input_filter_talk_forget_reserve_num.value)
                config_data["filter"]["schedule_forget_duration"] = round(float(input_filter_schedule_forget_duration.value), 2)
                config_data["filter"]["schedule_forget_reserve_num"] = int(input_filter_schedule_forget_reserve_num.value)

                # Thanks
                config_data["thanks"]["username_max_len"] = int(input_thanks_username_max_len.value)
                config_data["thanks"]["entrance_enable"] = switch_thanks_entrance_enable.value
                config_data["thanks"]["entrance_random"] = switch_thanks_entrance_random.value
                config_data["thanks"]["entrance_copy"] = common_textarea_handle(textarea_thanks_entrance_copy.value)
                config_data["thanks"]["gift_enable"] = switch_thanks_gift_enable.value
                config_data["thanks"]["gift_random"] = switch_thanks_gift_random.value
                config_data["thanks"]["gift_copy"] = common_textarea_handle(textarea_thanks_gift_copy.value)
                config_data["thanks"]["lowest_price"] = round(float(input_thanks_lowest_price.value), 2)
                config_data["thanks"]["follow_enable"] = switch_thanks_follow_enable.value
                config_data["thanks"]["follow_random"] = switch_thanks_follow_random.value
                config_data["thanks"]["follow_copy"] = common_textarea_handle(textarea_thanks_follow_copy.value)

                # Audio random speed
                config_data["audio_random_speed"]["normal"]["enable"] = switch_audio_random_speed_normal_enable.value
                config_data["audio_random_speed"]["normal"]["speed_min"] = round(float(input_audio_random_speed_normal_speed_min.value), 2)
                config_data["audio_random_speed"]["normal"]["speed_max"] = round(float(input_audio_random_speed_normal_speed_max.value), 2)
                config_data["audio_random_speed"]["copywriting"]["enable"] = switch_audio_random_speed_copywriting_enable.value
                config_data["audio_random_speed"]["copywriting"]["speed_min"] = round(float(input_audio_random_speed_copywriting_speed_min.value), 2)
                config_data["audio_random_speed"]["copywriting"]["speed_max"] = round(float(input_audio_random_speed_copywriting_speed_max.value), 2)

                # Song request mode
                config_data["choose_song"]["enable"] = switch_choose_song_enable.value
                config_data["choose_song"]["start_cmd"] = common_textarea_handle(textarea_choose_song_start_cmd.value)
                config_data["choose_song"]["stop_cmd"] = common_textarea_handle(textarea_choose_song_stop_cmd.value)
                config_data["choose_song"]["random_cmd"] = common_textarea_handle(textarea_choose_song_random_cmd.value)
                config_data["choose_song"]["song_path"] = input_choose_song_song_path.value
                config_data["choose_song"]["match_fail_copy"] = input_choose_song_match_fail_copy.value
                config_data["choose_song"]["similarity"] = round(float(input_choose_song_similarity.value), 2)

                # Scheduled tasks
                tmp_arr = []
                # logging.info(schedule_var)
                for index in range(len(schedule_var) // 3):
                    tmp_json = {
                        "enable": False,
                        "time": 60,
                        "copy": []
                    }
                    tmp_json["enable"] = schedule_var[str(3 * index)].value
                    tmp_json["time"] = round(float(schedule_var[str(3 * index + 1)].value), 1)
                    tmp_json["copy"] = common_textarea_handle(schedule_var[str(3 * index + 2)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["schedule"] = tmp_arr

                # Idle time tasks
                config_data["idle_time_task"]["enable"] = switch_idle_time_task_enable.value
                config_data["idle_time_task"]["idle_time"] = input_idle_time_task_idle_time.value
                config_data["idle_time_task"]["random_time"] = switch_idle_time_task_random_time.value
                config_data["idle_time_task"]["comment"]["enable"] = switch_idle_time_task_comment_enable.value
                config_data["idle_time_task"]["comment"]["random"] = switch_idle_time_task_comment_random.value
                config_data["idle_time_task"]["comment"]["copy"] = common_textarea_handle(textarea_idle_time_task_comment_copy.value)
                config_data["idle_time_task"]["local_audio"]["enable"] = switch_idle_time_task_local_audio_enable.value
                config_data["idle_time_task"]["local_audio"]["random"] = switch_idle_time_task_local_audio_random.value
                config_data["idle_time_task"]["local_audio"]["path"] = common_textarea_handle(textarea_idle_time_task_local_audio_path.value)

                # SD
                config_data["sd"]["enable"] = switch_sd_enable.value
                config_data["sd"]["prompt_llm"]["type"] = select_sd_prompt_llm_type.value
                config_data["sd"]["prompt_llm"]["before_prompt"] = input_sd_prompt_llm_before_prompt.value
                config_data["sd"]["prompt_llm"]["after_prompt"] = input_sd_prompt_llm_after_prompt.value
                config_data["sd"]["trigger"] = input_sd_trigger.value
                config_data["sd"]["ip"] = input_sd_ip.value
                sd_port = input_sd_port.value
                config_data["sd"]["port"] = int(sd_port)
                config_data["sd"]["negative_prompt"] = input_sd_negative_prompt.value
                config_data["sd"]["seed"] = float(input_sd_seed.value)
                # Get the content of the multiline text input box
                config_data["sd"]["styles"] = common_textarea_handle(textarea_sd_styles.value)
                config_data["sd"]["cfg_scale"] = int(input_sd_cfg_scale.value)
                config_data["sd"]["steps"] = int(input_sd_steps.value)
                config_data["sd"]["hr_resize_x"] = int(input_sd_hr_resize_x.value)
                config_data["sd"]["hr_resize_y"] = int(input_sd_hr_resize_y.value)
                config_data["sd"]["enable_hr"] = switch_sd_enable_hr.value
                config_data["sd"]["hr_scale"] = int(input_sd_hr_scale.value)
                config_data["sd"]["hr_second_pass_steps"] = int(input_sd_hr_second_pass_steps.value)
                config_data["sd"]["denoising_strength"] = round(float(input_sd_denoising_strength.value), 1)

                # Dynamic copywriting
                config_data["trends_copywriting"]["enable"] = switch_trends_copywriting_enable.value
                config_data["trends_copywriting"]["random_play"] = switch_trends_copywriting_random_play.value
                config_data["trends_copywriting"]["play_interval"] = int(input_trends_copywriting_play_interval.value)
                tmp_arr = []
                for index in range(len(trends_copywriting_copywriting_var) // 3):
                    tmp_json = {
                        "folder_path": "",
                        "prompt_change_enable": False,
                        "prompt_change_content": ""
                    }
                    tmp_json["folder_path"] = trends_copywriting_copywriting_var[str(3 * index)].value
                    tmp_json["prompt_change_enable"] = trends_copywriting_copywriting_var[str(3 * index + 1)].value
                    tmp_json["prompt_change_content"] = trends_copywriting_copywriting_var[str(3 * index + 2)].value

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["trends_copywriting"]["copywriting"] = tmp_arr

                # Web subtitles printer
                config_data["web_captions_printer"]["enable"] = switch_web_captions_printer_enable.value
                config_data["web_captions_printer"]["api_ip_port"] = input_web_captions_printer_api_ip_port.value

                # Database
                config_data["database"]["path"] = input_database_path.value
                config_data["database"]["comment_enable"] = switch_database_comment_enable.value
                config_data["database"]["entrance_enable"] = switch_database_entrance_enable.value
                config_data["database"]["gift_enable"] = switch_database_gift_enable.value

                # Key mapping
                config_data["key_mapping"]["enable"] = switch_key_mapping_enable.value
                config_data["key_mapping"]["type"] = select_key_mapping_type.value
                # logging.info(select_key_mapping_type.value)
                config_data["key_mapping"]["start_cmd"] = input_key_mapping_start_cmd.value
                tmp_arr = []
                # logging.info(key_mapping_config_var)
                for index in range(len(key_mapping_config_var) // 3):
                    tmp_json = {
                        "keywords": [],
                        "keys": [],
                        "similarity": 1
                    }
                    tmp_json["keywords"] = common_textarea_handle(key_mapping_config_var[str(3 * index)].value)
                    tmp_json["keys"] = common_textarea_handle(key_mapping_config_var[str(3 * index + 1)].value)
                    tmp_json["similarity"] = key_mapping_config_var[str(3 * index + 2)].value

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["key_mapping"]["config"] = tmp_arr

                # Dynamic configuration
                config_data["trends_config"]["enable"] = switch_trends_config_enable.value
                tmp_arr = []
                # logging.info(trends_config_path_var)
                for index in range(len(trends_config_path_var) // 2):
                    tmp_json = {
                        "online_num": "0-999999999",
                        "path": "config.json"
                    }
                    tmp_json["online_num"] = trends_config_path_var[str(2 * index)].value
                    tmp_json["path"] = trends_config_path_var[str(2 * index + 1)].value

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["trends_config"]["path"] = tmp_arr

                # Abnormal alarm / ALERT MODE
                config_data["abnormal_alarm"]["platform"]["enable"] = switch_abnormal_alarm_platform_enable.value
                config_data["abnormal_alarm"]["platform"]["type"] = select_abnormal_alarm_platform_type.value
                config_data["abnormal_alarm"]["platform"]["start_alarm_error_num"] = int(input_abnormal_alarm_platform_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["platform"]["auto_restart_error_num"] = int(input_abnormal_alarm_platform_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["platform"]["local_audio_path"] = input_abnormal_alarm_platform_local_audio_path.value
                config_data["abnormal_alarm"]["llm"]["enable"] = switch_abnormal_alarm_llm_enable.value
                config_data["abnormal_alarm"]["llm"]["type"] = select_abnormal_alarm_llm_type.value
                config_data["abnormal_alarm"]["llm"]["start_alarm_error_num"] = int(input_abnormal_alarm_llm_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["llm"]["auto_restart_error_num"] = int(input_abnormal_alarm_llm_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["llm"]["local_audio_path"] = input_abnormal_alarm_llm_local_audio_path.value
                config_data["abnormal_alarm"]["tts"]["enable"] = switch_abnormal_alarm_tts_enable.value
                config_data["abnormal_alarm"]["tts"]["type"] = select_abnormal_alarm_tts_type.value
                config_data["abnormal_alarm"]["tts"]["start_alarm_error_num"] = int(input_abnormal_alarm_tts_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["tts"]["auto_restart_error_num"] = int(input_abnormal_alarm_tts_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["tts"]["local_audio_path"] = input_abnormal_alarm_tts_local_audio_path.value
                config_data["abnormal_alarm"]["svc"]["enable"] = switch_abnormal_alarm_svc_enable.value
                config_data["abnormal_alarm"]["svc"]["type"] = select_abnormal_alarm_svc_type.value
                config_data["abnormal_alarm"]["svc"]["start_alarm_error_num"] = int(input_abnormal_alarm_svc_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["svc"]["auto_restart_error_num"] = int(input_abnormal_alarm_svc_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["svc"]["local_audio_path"] = input_abnormal_alarm_svc_local_audio_path.value
                config_data["abnormal_alarm"]["visual_body"]["enable"] = switch_abnormal_alarm_visual_body_enable.value
                config_data["abnormal_alarm"]["visual_body"]["type"] = select_abnormal_alarm_visual_body_type.value
                config_data["abnormal_alarm"]["visual_body"]["start_alarm_error_num"] = int(input_abnormal_alarm_visual_body_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["visual_body"]["auto_restart_error_num"] = int(input_abnormal_alarm_visual_body_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["visual_body"]["local_audio_path"] = input_abnormal_alarm_visual_body_local_audio_path.value
                config_data["abnormal_alarm"]["other"]["enable"] = switch_abnormal_alarm_other_enable.value
                config_data["abnormal_alarm"]["other"]["type"] = select_abnormal_alarm_other_type.value
                config_data["abnormal_alarm"]["other"]["start_alarm_error_num"] = int(input_abnormal_alarm_other_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["other"]["auto_restart_error_num"] = int(input_abnormal_alarm_other_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["other"]["local_audio_path"] = input_abnormal_alarm_other_local_audio_path.value

            """
            LLM
            """
            if True:
                config_data["openai"]["api"] = input_openai_api.value
                config_data["openai"]["api_key"] = common_textarea_handle(textarea_openai_api_key.value)
                # logging.info(select_chatgpt_model.value)
                config_data["chatgpt"]["model"] = select_chatgpt_model.value
                config_data["chatgpt"]["temperature"] = round(float(input_chatgpt_temperature.value), 1)
                config_data["chatgpt"]["max_tokens"] = int(input_chatgpt_max_tokens.value)
                config_data["chatgpt"]["top_p"] = round(float(input_chatgpt_top_p.value), 1)
                config_data["chatgpt"]["presence_penalty"] = round(float(input_chatgpt_presence_penalty.value), 1)
                config_data["chatgpt"]["frequency_penalty"] = round(float(input_chatgpt_frequency_penalty.value), 1)
                config_data["chatgpt"]["preset"] = input_chatgpt_preset.value

                config_data["claude"]["slack_user_token"] = input_claude_slack_user_token.value
                config_data["claude"]["bot_user_id"] = input_claude_bot_user_id.value

                config_data["claude2"]["cookie"] = input_claude2_cookie.value
                config_data["claude2"]["use_proxy"] = switch_claude2_use_proxy.value
                config_data["claude2"]["proxies"]["http"] = input_claude2_proxies_http.value
                config_data["claude2"]["proxies"]["https"] = input_claude2_proxies_https.value
                config_data["claude2"]["proxies"]["socks5"] = input_claude2_proxies_socks5.value

                config_data["chatglm"]["api_ip_port"] = input_chatglm_api_ip_port.value
                config_data["chatglm"]["max_length"] = int(input_chatglm_max_length.value)
                config_data["chatglm"]["top_p"] = round(float(input_chatglm_top_p.value), 1)
                config_data["chatglm"]["temperature"] = round(float(input_chatglm_temperature.value), 2)
                config_data["chatglm"]["history_enable"] = switch_chatglm_history_enable.value
                config_data["chatglm"]["history_max_len"] = int(input_chatglm_history_max_len.value)

                config_data["chat_with_file"]["chat_mode"] = select_chat_with_file_chat_mode.value
                config_data["chat_with_file"]["data_path"] = input_chat_with_file_data_path.value
                config_data["chat_with_file"]["separator"] = input_chat_with_file_separator.value
                config_data["chat_with_file"]["chunk_size"] = int(input_chat_with_file_chunk_size.value)
                config_data["chat_with_file"]["chunk_overlap"] = int(input_chat_with_file_chunk_overlap.value)
                config_data["chat_with_file"]["local_vector_embedding_model"] = select_chat_with_file_local_vector_embedding_model.value
                config_data["chat_with_file"]["chain_type"] = input_chat_with_file_chain_type.value
                config_data["chat_with_file"]["question_prompt"] = input_chat_with_file_question_prompt.value
                config_data["chat_with_file"]["local_max_query"] = int(input_chat_with_file_local_max_query.value)
                config_data["chat_with_file"]["show_token_cost"] = switch_chat_with_file_show_token_cost.value

                config_data["chatterbot"]["name"] = input_chatterbot_name.value
                config_data["chatterbot"]["db_path"] = input_chatterbot_db_path.value

                config_data["text_generation_webui"]["type"] = select_text_generation_webui_type.value
                config_data["text_generation_webui"]["api_ip_port"] = input_text_generation_webui_api_ip_port.value
                config_data["text_generation_webui"]["max_new_tokens"] = int(input_text_generation_webui_max_new_tokens.value)
                config_data["text_generation_webui"]["history_enable"] = switch_text_generation_webui_history_enable.value
                config_data["text_generation_webui"]["history_max_len"] = int(input_text_generation_webui_history_max_len.value)
                config_data["text_generation_webui"]["mode"] = select_text_generation_webui_mode.value
                config_data["text_generation_webui"]["character"] = input_text_generation_webui_character.value
                config_data["text_generation_webui"]["instruction_template"] = input_text_generation_webui_instruction_template.value
                config_data["text_generation_webui"]["your_name"] = input_text_generation_webui_your_name.value
                config_data["text_generation_webui"]["top_p"] = round(float(input_text_generation_webui_top_p.value), 2)
                config_data["text_generation_webui"]["top_k"] = int(input_text_generation_webui_top_k.value)
                config_data["text_generation_webui"]["temperature"] = round(float(input_text_generation_webui_temperature.value), 2)
                config_data["text_generation_webui"]["seed"] = float(input_text_generation_webui_seed.value)

                config_data["sparkdesk"]["type"] = select_sparkdesk_type.value
                config_data["sparkdesk"]["cookie"] = input_sparkdesk_cookie.value
                config_data["sparkdesk"]["fd"] = input_sparkdesk_fd.value
                config_data["sparkdesk"]["GtToken"] = input_sparkdesk_GtToken.value
                config_data["sparkdesk"]["app_id"] = input_sparkdesk_app_id.value
                config_data["sparkdesk"]["api_secret"] = input_sparkdesk_api_secret.value
                config_data["sparkdesk"]["api_key"] = input_sparkdesk_api_key.value
                config_data["sparkdesk"]["version"] = round(float(select_sparkdesk_version.value), 1)

                config_data["langchain_chatglm"]["api_ip_port"] = input_langchain_chatglm_api_ip_port.value
                config_data["langchain_chatglm"]["chat_type"] = select_langchain_chatglm_chat_type.value
                config_data["langchain_chatglm"]["knowledge_base_id"] = input_langchain_chatglm_knowledge_base_id.value
                config_data["langchain_chatglm"]["history_enable"] = switch_langchain_chatglm_history_enable.value
                config_data["langchain_chatglm"]["history_max_len"] = int(input_langchain_chatglm_history_max_len.value)

                config_data["langchain_chatchat"]["api_ip_port"] = input_langchain_chatchat_api_ip_port.value
                config_data["langchain_chatchat"]["chat_type"] = select_langchain_chatchat_chat_type.value
                config_data["langchain_chatchat"]["history_enable"] = switch_langchain_chatchat_history_enable.value
                config_data["langchain_chatchat"]["history_max_len"] = int(input_langchain_chatchat_history_max_len.value)
                config_data["langchain_chatchat"]["llm"]["model_name"] = input_langchain_chatchat_llm_model_name.value
                config_data["langchain_chatchat"]["llm"]["temperature"] = round(float(input_langchain_chatchat_llm_temperature.value), 2)
                config_data["langchain_chatchat"]["llm"]["max_tokens"] = int(input_langchain_chatchat_llm_max_tokens.value)
                config_data["langchain_chatchat"]["llm"]["prompt_name"] = input_langchain_chatchat_llm_prompt_name.value
                config_data["langchain_chatchat"]["knowledge_base"]["knowledge_base_name"] = input_langchain_chatchat_knowledge_base_knowledge_base_name.value
                config_data["langchain_chatchat"]["knowledge_base"]["top_k"] = int(input_langchain_chatchat_knowledge_base_top_k.value)
                config_data["langchain_chatchat"]["knowledge_base"]["score_threshold"] = round(float(input_langchain_chatchat_knowledge_base_score_threshold.value), 2)
                config_data["langchain_chatchat"]["knowledge_base"]["model_name"] = input_langchain_chatchat_knowledge_base_model_name.value
                config_data["langchain_chatchat"]["knowledge_base"]["temperature"] = round(float(input_langchain_chatchat_knowledge_base_temperature.value), 2)
                config_data["langchain_chatchat"]["knowledge_base"]["max_tokens"] = int(input_langchain_chatchat_knowledge_base_max_tokens.value)
                config_data["langchain_chatchat"]["knowledge_base"]["prompt_name"] = input_langchain_chatchat_knowledge_base_prompt_name.value
                config_data["langchain_chatchat"]["search_engine"]["search_engine_name"] = select_langchain_chatchat_search_engine_search_engine_name.value
                config_data["langchain_chatchat"]["search_engine"]["top_k"] = int(input_langchain_chatchat_search_engine_top_k.value)
                config_data["langchain_chatchat"]["search_engine"]["model_name"] = input_langchain_chatchat_search_engine_model_name.value
                config_data["langchain_chatchat"]["search_engine"]["temperature"] = round(float(input_langchain_chatchat_search_engine_temperature.value), 2)
                config_data["langchain_chatchat"]["search_engine"]["max_tokens"] = int(input_langchain_chatchat_search_engine_max_tokens.value)
                config_data["langchain_chatchat"]["search_engine"]["prompt_name"] = input_langchain_chatchat_search_engine_prompt_name.value


                config_data["zhipu"]["api_key"] = input_zhipu_api_key.value
                config_data["zhipu"]["model"] = select_zhipu_model.value
                config_data["zhipu"]["top_p"] = input_zhipu_top_p.value
                config_data["zhipu"]["temperature"] = input_zhipu_temperature.value
                config_data["zhipu"]["history_enable"] = switch_zhipu_history_enable.value
                config_data["zhipu"]["history_max_len"] = input_zhipu_history_max_len.value
                config_data["zhipu"]["user_info"] = input_zhipu_user_info.value
                config_data["zhipu"]["bot_info"] = input_zhipu_bot_info.value
                config_data["zhipu"]["bot_name"] = input_zhipu_bot_name.value
                config_data["zhipu"]["user_name"] = input_zhipu_user_name.value
                config_data["zhipu"]["remove_useless"] = switch_zhipu_remove_useless.value

                config_data["bard"]["token"] = input_bard_token.value

                config_data["yiyan"]["type"] = select_yiyan_type.value
                config_data["yiyan"]["history_enable"] = switch_yiyan_history_enable.value
                config_data["yiyan"]["history_max_len"] = int(input_yiyan_history_max_len.value)
                config_data["yiyan"]["api"]["api_key"] = input_yiyan_api_api_key.value
                config_data["yiyan"]["api"]["secret_key"] = input_yiyan_api_secret_key.value
                config_data["yiyan"]["web"]["api_ip_port"] = input_yiyan_web_api_ip_port.value
                config_data["yiyan"]["web"]["cookie"] = input_yiyan_web_cookie.value

                config_data["tongyi"]["type"] = select_tongyi_type.value
                config_data["tongyi"]["cookie_path"] = input_tongyi_cookie_path.value

                config_data["tongyixingchen"]["access_token"] = input_tongyixingchen_access_token.value
                config_data["tongyixingchen"]["type"] = select_tongyixingchen_type.value
                config_data["tongyixingchen"]["history_enable"] = switch_tongyixingchen_history_enable.value
                config_data["tongyixingchen"]["history_max_len"] = input_tongyixingchen_history_max_len.value
                config_data["tongyixingchen"]["固定角色"]["character_id"] = input_tongyixingchen_GDJS_character_id.value
                config_data["tongyixingchen"]["固定角色"]["top_p"] = round(float(input_tongyixingchen_GDJS_top_p.value), 2)
                config_data["tongyixingchen"]["固定角色"]["temperature"] = round(float(input_tongyixingchen_GDJS_temperature.value), 2)
                config_data["tongyixingchen"]["固定角色"]["seed"] = int(input_tongyixingchen_GDJS_seed.value)
                config_data["tongyixingchen"]["固定角色"]["user_id"] = input_tongyixingchen_GDJS_user_id.value
                config_data["tongyixingchen"]["固定角色"]["user_name"] = input_tongyixingchen_GDJS_user_name.value
                config_data["tongyixingchen"]["固定角色"]["role_name"] = input_tongyixingchen_GDJS_role_name.value

                # config_data["my_qianfan"]["model"] = select_my_qianfan_model.value
                # config_data["my_qianfan"]["access_key"] = input_my_qianfan_access_key.value
                # config_data["my_qianfan"]["secret_key"] = input_my_qianfan_secret_key.value
                # config_data["my_qianfan"]["top_p"] = round(float(input_my_qianfan_top_p.value), 2)
                # config_data["my_qianfan"]["temperature"] = round(float(input_my_qianfan_temperature.value), 2)
                # config_data["my_qianfan"]["penalty_score"] = round(float(input_my_qianfan_penalty_score.value), 2)
                # config_data["my_qianfan"]["history_enable"] = switch_my_qianfan_history_enable.value
                # config_data["my_qianfan"]["history_max_len"] = int(input_my_qianfan_history_max_len.value)

                config_data["my_wenxinworkshop"]["model"] = select_my_wenxinworkshop_model.value
                config_data["my_wenxinworkshop"]["api_key"] = input_my_wenxinworkshop_api_key.value
                config_data["my_wenxinworkshop"]["secret_key"] = input_my_wenxinworkshop_secret_key.value
                config_data["my_wenxinworkshop"]["top_p"] = round(float(input_my_wenxinworkshop_top_p.value), 2)
                config_data["my_wenxinworkshop"]["temperature"] = round(float(input_my_wenxinworkshop_temperature.value), 2)
                config_data["my_wenxinworkshop"]["penalty_score"] = round(float(input_my_wenxinworkshop_penalty_score.value), 2)
                config_data["my_wenxinworkshop"]["history_enable"] = switch_my_wenxinworkshop_history_enable.value
                config_data["my_wenxinworkshop"]["history_max_len"] = int(input_my_wenxinworkshop_history_max_len.value)

                config_data["gemini"]["api_key"] = input_gemini_api_key.value
                config_data["gemini"]["model"] = select_gemini_model.value
                config_data["gemini"]["history_enable"] = switch_gemini_history_enable.value
                config_data["gemini"]["history_max_len"] = int(input_gemini_history_max_len.value)
                config_data["gemini"]["http_proxy"] = input_gemini_http_proxy.value
                config_data["gemini"]["https_proxy"] = input_gemini_https_proxy.value
                config_data["gemini"]["max_output_tokens"] = int(input_gemini_max_output_tokens.value)
                config_data["gemini"]["temperature"] = round(float(input_gemini_max_temperature.value), 2)
                config_data["gemini"]["top_p"] = round(float(input_gemini_top_p.value), 2)
                config_data["gemini"]["top_k"] = int(input_gemini_top_k.value)

            """
            TTS
            """
            if True:
                config_data["edge-tts"]["voice"] = select_edge_tts_voice.value
                config_data["edge-tts"]["rate"] = input_edge_tts_rate.value
                config_data["edge-tts"]["volume"] = input_edge_tts_volume.value

                config_data["vits"]["type"] = select_vits_type.value
                config_data["vits"]["config_path"] = input_vits_config_path.value
                config_data["vits"]["api_ip_port"] = input_vits_api_ip_port.value
                config_data["vits"]["id"] = input_vits_id.value
                config_data["vits"]["lang"] = select_vits_lang.value
                config_data["vits"]["length"] = input_vits_length.value
                config_data["vits"]["noise"] = input_vits_noise.value
                config_data["vits"]["noisew"] = input_vits_noisew.value
                config_data["vits"]["max"] = input_vits_max.value
                config_data["vits"]["format"] = input_vits_format.value
                config_data["vits"]["sdp_radio"] = input_vits_sdp_radio.value

                config_data["bert_vits2"]["type"] = select_bert_vits2_type.value
                config_data["bert_vits2"]["api_ip_port"] = input_bert_vits2_api_ip_port.value
                config_data["bert_vits2"]["model_id"] = int(input_vits_model_id.value)
                config_data["bert_vits2"]["speaker_name"] = input_vits_speaker_name.value
                config_data["bert_vits2"]["speaker_id"] = int(input_vits_speaker_id.value)
                config_data["bert_vits2"]["language"] = select_bert_vits2_language.value
                config_data["bert_vits2"]["length"] = round(float(input_bert_vits2_length.value), 2)
                config_data["bert_vits2"]["noise"] = round(float(input_bert_vits2_noise.value), 2)
                config_data["bert_vits2"]["noisew"] = round(float(input_bert_vits2_noisew.value), 2)
                config_data["bert_vits2"]["sdp_radio"] = round(float(input_bert_vits2_sdp_radio.value), 2)
                config_data["bert_vits2"]["emotion"] = input_bert_vits2_emotion.value
                config_data["bert_vits2"]["style_text"] = input_bert_vits2_style_text.value
                config_data["bert_vits2"]["style_weight"] = round(float(input_bert_vits2_style_weight.value), 2)
                config_data["bert_vits2"]["auto_translate"] = switch_bert_vits2_auto_translate.value
                config_data["bert_vits2"]["auto_split"] = switch_bert_vits2_auto_split.value

                config_data["vits_fast"]["config_path"] = input_vits_fast_config_path.value
                config_data["vits_fast"]["api_ip_port"] = input_vits_fast_api_ip_port.value
                config_data["vits_fast"]["character"] = input_vits_fast_character.value
                config_data["vits_fast"]["language"] = select_vits_fast_language.value
                config_data["vits_fast"]["speed"] = input_vits_fast_speed.value
                
                config_data["elevenlabs"]["api_key"] = input_elevenlabs_api_key.value
                config_data["elevenlabs"]["voice"] = input_elevenlabs_voice.value
                config_data["elevenlabs"]["model"] = input_elevenlabs_model.value

                config_data["genshinvoice_top"]["speaker"] = select_genshinvoice_top_speaker.value
                config_data["genshinvoice_top"]["noise"] = input_genshinvoice_top_noise.value
                config_data["genshinvoice_top"]["noisew"] = input_genshinvoice_top_noisew.value
                config_data["genshinvoice_top"]["length"] = input_genshinvoice_top_length.value
                config_data["genshinvoice_top"]["format"] = input_genshinvoice_top_format.value
                config_data["genshinvoice_top"]["language"] = select_genshinvoice_top_language.value

                config_data["tts_ai_lab_top"]["speaker"] = select_tts_ai_lab_top_speaker.value
                config_data["tts_ai_lab_top"]["appid"] = input_tts_ai_lab_top_appid.value
                config_data["tts_ai_lab_top"]["token"] = input_tts_ai_lab_top_token.value
                config_data["tts_ai_lab_top"]["noise"] = input_tts_ai_lab_top_noise.value
                config_data["tts_ai_lab_top"]["noisew"] = input_tts_ai_lab_top_noisew.value
                config_data["tts_ai_lab_top"]["length"] = input_tts_ai_lab_top_length.value
                config_data["tts_ai_lab_top"]["sdp_ratio"] = input_tts_ai_lab_top_sdp_ratio.value

                config_data["bark_gui"]["api_ip_port"] = input_bark_gui_api_ip_port.value
                config_data["bark_gui"]["spk"] = input_bark_gui_spk.value
                config_data["bark_gui"]["generation_temperature"] = input_bark_gui_generation_temperature.value
                config_data["bark_gui"]["waveform_temperature"] = input_bark_gui_waveform_temperature.value
                config_data["bark_gui"]["end_of_sentence_probability"] = input_bark_gui_end_of_sentence_probability.value
                config_data["bark_gui"]["quick_generation"] = switch_bark_gui_quick_generation.value
                config_data["bark_gui"]["seed"] = input_bark_gui_seed.value
                config_data["bark_gui"]["batch_count"] = input_bark_gui_batch_count.value

                config_data["vall_e_x"]["api_ip_port"] = input_vall_e_x_api_ip_port.value
                config_data["vall_e_x"]["language"] = select_vall_e_x_language.value
                config_data["vall_e_x"]["accent"] = select_vall_e_x_accent.value
                config_data["vall_e_x"]["voice_preset"] = input_vall_e_x_voice_preset.value
                config_data["vall_e_x"]["voice_preset_file_path"] = input_vall_e_x_voice_preset_file_path.value

                config_data["openai_tts"]["type"] = select_openai_tts_type.value
                config_data["openai_tts"]["api_ip_port"] = input_openai_tts_api_ip_port.value
                config_data["openai_tts"]["model"] = select_openai_tts_model.value
                config_data["openai_tts"]["voice"] = select_openai_tts_voice.value
                config_data["openai_tts"]["api_key"] = input_openai_tts_api_key.value
                
                config_data["reecho_ai"]["Authorization"] = input_reecho_ai_Authorization.value
                config_data["reecho_ai"]["model"] = input_reecho_ai_model.value
                config_data["reecho_ai"]["voiceId"] = input_reecho_ai_voiceId.value
                config_data["reecho_ai"]["randomness"] = int(number_reecho_ai_randomness.value)
                config_data["reecho_ai"]["stability_boost"] = int(number_reecho_ai_stability_boost.value)

                config_data["gradio_tts"]["request_parameters"] = textarea_gradio_tts_request_parameters.value
        
            """
            SVC
            """
            if True:
                config_data["ddsp_svc"]["enable"] = switch_ddsp_svc_enable.value
                config_data["ddsp_svc"]["config_path"] = input_ddsp_svc_config_path.value
                config_data["ddsp_svc"]["api_ip_port"] = input_ddsp_svc_api_ip_port.value
                config_data["ddsp_svc"]["fSafePrefixPadLength"] = round(float(input_ddsp_svc_fSafePrefixPadLength.value), 1)
                config_data["ddsp_svc"]["fPitchChange"] = round(float(input_ddsp_svc_fPitchChange.value), 1)
                config_data["ddsp_svc"]["sSpeakId"] = int(input_ddsp_svc_sSpeakId.value)
                config_data["ddsp_svc"]["sampleRate"] = int(input_ddsp_svc_sampleRate.value)

                config_data["so_vits_svc"]["enable"] = switch_so_vits_svc_enable.value
                config_data["so_vits_svc"]["config_path"] = input_so_vits_svc_config_path.value
                config_data["so_vits_svc"]["api_ip_port"] = input_so_vits_svc_api_ip_port.value
                config_data["so_vits_svc"]["spk"] = input_so_vits_svc_spk.value
                config_data["so_vits_svc"]["tran"] = round(float(input_so_vits_svc_tran.value), 1)
                config_data["so_vits_svc"]["wav_format"] = input_so_vits_svc_wav_format.value

            """
            Virtual body / Live2D
            """
            if True:
                config_data["live2d"]["enable"] = switch_live2d_enable.value
                config_data["live2d"]["port"] = int(input_live2d_port.value)
                # config_data["live2d"]["name"] = input_live2d_name.value
                
                config_data["xuniren"]["api_ip_port"] = input_xuniren_api_ip_port.value

                # config_data["unity"]["enable"] = switch_unity_enable.value
                config_data["unity"]["api_ip_port"] = input_unity_api_ip_port.value
                config_data["unity"]["password"] = input_unity_password.value
                    
            """
            Copywriting
            """
            if True:
                config_data["copywriting"]["auto_play"] = switch_copywriting_auto_play.value
                config_data["copywriting"]["random_play"] = switch_copywriting_random_play.value
                config_data["copywriting"]["audio_interval"] = input_copywriting_audio_interval.value
                config_data["copywriting"]["switching_interval"] = input_copywriting_switching_interval.value
                
                tmp_arr = []
                # logging.info(copywriting_config_var)
                for index in range(len(copywriting_config_var) // 5):
                    tmp_json = {
                        "file_path": "",
                        "audio_path": "",
                        "continuous_play_num": 1,
                        "max_play_time": 10.0,
                        "play_list": []
                    }
                    tmp_json["file_path"] = copywriting_config_var[str(5 * index)].value
                    tmp_json["audio_path"] = copywriting_config_var[str(5 * index + 1)].value
                    tmp_json["continuous_play_num"] = int(copywriting_config_var[str(5 * index + 2)].value)
                    tmp_json["max_play_time"] = float(copywriting_config_var[str(5 * index + 3)].value)
                    tmp_json["play_list"] = common_textarea_handle(copywriting_config_var[str(5 * index + 4)].value)
                    

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["copywriting"]["config"] = tmp_arr

            """
            Integral
            """
            if True:
                config_data["integral"]["enable"] = switch_integral_enable.value

                config_data["integral"]["sign"]["enable"] = switch_integral_sign_enable.value
                config_data["integral"]["sign"]["get_integral"] = int(input_integral_sign_get_integral.value)
                config_data["integral"]["sign"]["cmd"] = common_textarea_handle(textarea_integral_sign_cmd.value)
                tmp_arr = []
                # logging.info(integral_sign_copywriting_var)
                for index in range(len(integral_sign_copywriting_var) // 2):
                    tmp_json = {
                        "sign_num_interval": "",
                        "copywriting": []
                    }
                    tmp_json["sign_num_interval"] = integral_sign_copywriting_var[str(2 * index)].value
                    tmp_json["copywriting"] = common_textarea_handle(integral_sign_copywriting_var[str(2 * index + 1)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["integral"]["sign"]["copywriting"] = tmp_arr

                config_data["integral"]["gift"]["enable"] = switch_integral_gift_enable.value
                config_data["integral"]["gift"]["get_integral_proportion"] = float(input_integral_gift_get_integral_proportion.value)
                tmp_arr = []
                for index in range(len(integral_gift_copywriting_var) // 2):
                    tmp_json = {
                        "gift_price_interval": "",
                        "copywriting": []
                    }
                    tmp_json["gift_price_interval"] = integral_gift_copywriting_var[str(2 * index)].value
                    tmp_json["copywriting"] = common_textarea_handle(integral_gift_copywriting_var[str(2 * index + 1)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["integral"]["gift"]["copywriting"] = tmp_arr

                config_data["integral"]["entrance"]["enable"] = switch_integral_entrance_enable.value
                config_data["integral"]["entrance"]["get_integral"] = int(input_integral_entrance_get_integral.value)
                tmp_arr = []
                for index in range(len(integral_entrance_copywriting_var) // 2):
                    tmp_json = {
                        "entrance_num_interval": "",
                        "copywriting": []
                    }
                    tmp_json["entrance_num_interval"] = integral_entrance_copywriting_var[str(2 * index)].value
                    tmp_json["copywriting"] = common_textarea_handle(integral_entrance_copywriting_var[str(2 * index + 1)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["integral"]["entrance"]["copywriting"] = tmp_arr

                config_data["integral"]["crud"]["query"]["enable"] = switch_integral_crud_query_enable.value
                config_data["integral"]["crud"]["query"]["cmd"] = common_textarea_handle(textarea_integral_crud_query_cmd.value)
                config_data["integral"]["crud"]["query"]["copywriting"] = common_textarea_handle(textarea_integral_crud_query_copywriting.value)

            """
            Talk
            """
            if True:
                config_data["talk"]["device_index"] = select_talk_device_index.value
                config_data["talk"]["username"] = input_talk_username.value
                config_data["talk"]["continuous_talk"] = switch_talk_continuous_talk.value
                config_data["talk"]["trigger_key"] = select_talk_trigger_key.value
                config_data["talk"]["stop_trigger_key"] = select_talk_stop_trigger_key.value
                config_data["talk"]["volume_threshold"] = float(input_talk_volume_threshold.value)
                config_data["talk"]["silence_threshold"] = float(input_talk_silence_threshold.value)
                config_data["talk"]["CHANNELS"] = int(input_talk_silence_CHANNELS.value)
                config_data["talk"]["RATE"] = int(input_talk_silence_RATE.value)
                config_data["talk"]["type"] = select_talk_type.value
                config_data["talk"]["google"]["tgt_lang"] = select_talk_google_tgt_lang.value
                config_data["talk"]["baidu"]["app_id"] = input_talk_baidu_app_id.value
                config_data["talk"]["baidu"]["api_key"] = input_talk_baidu_api_key.value
                config_data["talk"]["baidu"]["secret_key"] = input_talk_baidu_secret_key.value
                config_data["talk"]["faster_whisper"]["model_size"] = input_faster_whisper_model_size.value
                config_data["talk"]["faster_whisper"]["device"] = select_faster_whisper_device.value
                config_data["talk"]["faster_whisper"]["compute_type"] = select_faster_whisper_compute_type.value
                config_data["talk"]["faster_whisper"]["download_root"] = input_faster_whisper_download_root.value
                config_data["talk"]["faster_whisper"]["beam_size"] = int(input_faster_whisper_beam_size.value)

            """
            Assist broadcast
            """
            if True:
                config_data["assistant_anchor"]["enable"] = switch_assistant_anchor_enable.value
                config_data["assistant_anchor"]["username"] = input_assistant_anchor_username.value
                tmp_arr = []
                for index in range(len(assistant_anchor_type_var)):
                    if assistant_anchor_type_var[str(index)].value:
                        tmp_arr.append(assistant_anchor_type_var[str(index)].text)
                # logging.info(tmp_arr)
                config_data["assistant_anchor"]["type"] = tmp_arr
                config_data["assistant_anchor"]["local_qa"]["text"]["enable"] = switch_assistant_anchor_local_qa_text_enable.value
                local_qa_text_format = select_assistant_anchor_local_qa_text_format.value
                if local_qa_text_format == "自定义json":
                    config_data["assistant_anchor"]["local_qa"]["text"]["format"] = "json"
                elif local_qa_text_format == "一问一答":
                    config_data["assistant_anchor"]["local_qa"]["text"]["format"] = "text"
                config_data["assistant_anchor"]["local_qa"]["text"]["file_path"] = input_assistant_anchor_local_qa_text_file_path.value
                config_data["assistant_anchor"]["local_qa"]["text"]["similarity"] = round(float(input_assistant_anchor_local_qa_text_similarity.value), 2)
                config_data["assistant_anchor"]["local_qa"]["audio"]["enable"] = switch_assistant_anchor_local_qa_audio_enable.value
                config_data["assistant_anchor"]["local_qa"]["audio"]["type"] = select_assistant_anchor_local_qa_audio_type.value
                config_data["assistant_anchor"]["local_qa"]["audio"]["file_path"] = input_assistant_anchor_local_qa_audio_file_path.value
                config_data["assistant_anchor"]["local_qa"]["audio"]["similarity"] = round(float(input_assistant_anchor_local_qa_audio_similarity.value), 2)
            

            """
            Translate
            """
            if True:
                config_data["translate"]["enable"] = switch_translate_enable.value
                config_data["translate"]["type"] = select_translate_type.value
                config_data["translate"]["trans_type"] = select_translate_trans_type.value
                config_data["translate"]["baidu"]["appid"] = input_translate_baidu_appid.value
                config_data["translate"]["baidu"]["appkey"] = input_translate_baidu_appkey.value
                config_data["translate"]["baidu"]["from_lang"] = select_translate_baidu_from_lang.value
                config_data["translate"]["baidu"]["to_lang"] = select_translate_baidu_to_lang.value

            """
            WewUI configuration
            """
            if True:
                config_data["webui"]["title"] = input_webui_title.value
                config_data["webui"]["ip"] = input_webui_ip.value
                config_data["webui"]["port"] = int(input_webui_port.value)
                config_data["webui"]["auto_run"] = switch_webui_auto_run.value
                config_data["webui"]["theme"]["choose"] = select_webui_theme_choose.value

                config_data["login"]["enable"] = switch_login_enable.value
                config_data["login"]["username"] = input_login_username.value
                config_data["login"]["password"] = input_login_password.value

        except Exception as e:
            logging.error(f"Unable to write to the configuration file!\n{e}")
            ui.notify(position="top", type="negative", message=f"Unable to write to the configuration file!\n{e}")
            logging.error(traceback.format_exc())

        # return True

        try:
            with open(config_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                config_file.flush()  # Flush the buffer to ensure immediate effect

            logging.info("Configuration data has been successfully written to the file!")
            ui.notify(position="top", type="positive", message="Configuration data has been successfully written to the file!")

            return True
        except Exception as e:
            logging.error(f"Unable to write to the configuration file!\n{e}")
            ui.notify(position="top", type="negative", message=f"Unable to write to the configuration file!\n{e}")
            return False
    
    # Live2D thread
    try:
        if config.get("live2d", "enable"):
            web_server_port = int(config.get("live2d", "port"))
            threading.Thread(target=lambda: asyncio.run(web_server_thread(web_server_port))).start()
    except Exception as e:
        logging.error(traceback.format_exc())
        os._exit(0)


    with ui.tabs().classes('w-full') as tabs:
        common_config_page = ui.tab('Common Configuration')
        llm_page = ui.tab('Large Language Model')
        tts_page = ui.tab('Text to Speech')
        svc_page = ui.tab('Voice Change')
        visual_body_page = ui.tab('Virtual Body')
        copywriting_page = ui.tab('Copywriting')
        integral_page = ui.tab('Integral')
        talk_page = ui.tab('Chat')
        assistant_anchor_page = ui.tab('Assistant Anchor')
        translate_page = ui.tab('Translation')
        web_page = ui.tab('Page Configuration')
        docs_page = ui.tab('Documentation')
        about_page = ui.tab('About')

    with ui.tab_panels(tabs, value=common_config_page).classes('w-full'):
        with ui.tab_panel(common_config_page).style(tab_panel_css):
            with ui.row():
                select_platform = ui.select(
                    label='Platform', 
                    options={
                        'talk': 'Chat Mode', 
                        # 'bilibili': 'Bilibili', 
                        # 'bilibili2': 'Bilibili 2', 
                        # 'dy': 'Douyin', 
                        # 'ks': 'Kuaishou',
                        # 'wxlive': 'WeChat Video',
                        # 'douyu': 'Douyu', 
                        'youtube': 'YouTube', 
                        'twitch': 'Twitch'
                    }, 
                    value=config.get("platform")
                ).style("width:200px;")

                input_room_display_id = ui.input(label='Room ID', placeholder='Usually the letters or numbers after the last / in the room URL', value=config.get("room_display_id")).style("width:200px;")

                select_chat_type = ui.select(
                    label='Chat Type', 
                    options={
                        'none': 'Disabled', 
                        'reread': 'Repeater', 
                        'chatgpt': 'ChatGPT/Listening Talent', 
                        'claude': 'Claude', 
                        'claude2': 'Claude2',
                        'chatglm': 'ChatGLM',
                        'chat_with_file': 'chat_with_file',
                        'chatterbot': 'Chatterbot',
                        'text_generation_webui': 'text_generation_webui',
                        'sparkdesk': 'iFlytek Spark',
                        'langchain_chatglm': 'langchain_chatglm',
                        'langchain_chatchat': 'langchain_chatchat',
                        # 'zhipu': 'Zhipu AI',
                        'bard': 'Bard',
                        # 'yiyan': 'Wenxin Yiyuan',
                        # 'tongyixingchen': 'Tongyi Xingchen',
                        # 'my_wenxinworkshop': 'Qianfan Big Model',
                        'gemini': 'Gemini',
                        # 'tongyi': 'Tongyi Qianwen',
                    }, 
                    value=config.get("chat_type")
                ).style("width:200px;")

                select_visual_body = ui.select(label='Virtual Body', options={'xuniren': 'xuniren', 'unity': 'unity', 'other': 'Other'}, value=config.get("visual_body")).style("width:200px;")

                select_audio_synthesis_type = ui.select(
                    label='Text to Speech', 
                    options={
                        'edge-tts': 'Edge-TTS', 
                        'vits': 'VITS', 
                        'bert_vits2': 'bert_vits2',
                        'vits_fast': 'VITS-Fast', 
                        'elevenlabs': 'elevenlabs',
                        # 'genshinvoice_top': 'genshinvoice_top',
                        'tts_ai_lab_top': 'tts_ai_lab_top',
                        'bark_gui': 'bark_gui',
                        # 'vall_e_x': 'VALL-E-X',
                        'openai_tts': 'OpenAI TTS',
                        # 'reecho_ai': 'Reecho AI',
                        # 'gradio_tts': 'Gradio'
                    }, 
                    value=config.get("audio_synthesis_type")
                ).style("width:200px;")

            with ui.row():
                select_need_lang = ui.select(
                    label='Reply Language', 
                    options={'none': '所有', 'zh': '中文', 'en': '英文', 'jp': '日文'}, 
                    value=config.get("need_lang")
                ).style("width:200px;")

                input_before_prompt = ui.input(label='Prefix for Prompts', placeholder='This configuration will be appended to the front of the danmaku before being sent to LLM processing', value=config.get("before_prompt")).style("width:200px;")
                input_after_prompt = ui.input(label='Suffix for Prompts', placeholder='This configuration will be appended to the end of the danmaku before being sent to LLM processing', value=config.get("after_prompt")).style("width:200px;")
            
            # Bilibili Login
            with ui.card().style(card_css):
                ui.label('Bilibili')
                with ui.row():
                    select_bilibili_login_type = ui.select(
                        label='Login Method',
                        options={'Mobile Scan': 'Mobile Scan', 'Mobile Scan-Terminal': 'Mobile Scan-Terminal', 'Cookie': 'Cookie', 'Account Password Login': 'Account Password Login', 'Open Live': 'Open Platform', 'No Login': 'No Login'},
                        value=config.get("bilibili", "login_type")
                    ).style("width:100px")
                    input_bilibili_cookie = ui.input(label='Cookie', placeholder='Capture cookie by F12 after logging in to Bilibili, strongly recommend using a secondary account! Risk of ban', value=config.get("bilibili", "cookie")).style("width:500px;")
                    input_bilibili_ac_time_value = ui.input(label='ac_time_value', placeholder='After logging in to Bilibili, F12 console, enter window.localStorage.ac_time_value to get (if not, please log in again)', value=config.get("bilibili", "ac_time_value")).style("width:500px;")
                with ui.row():
                    input_bilibili_username = ui.input(label='Account', value=config.get("bilibili", "username"), placeholder='Bilibili account (recommended to use a secondary account)').style("width:300px;")
                    input_bilibili_password = ui.input(label='Password', value=config.get("bilibili", "password"), placeholder='Bilibili password (recommended to use a secondary account)').style("width:300px;")
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label('Open Platform')
                        with ui.row():
                            input_bilibili_open_live_ACCESS_KEY_ID = ui.input(label='ACCESS_KEY_ID', value=config.get("bilibili", "open_live", "ACCESS_KEY_ID"), placeholder='开放平台ACCESS_KEY_ID').style("width:300px;")
                            input_bilibili_open_live_ACCESS_KEY_SECRET = ui.input(label='ACCESS_KEY_SECRET', value=config.get("bilibili", "open_live", "ACCESS_KEY_SECRET"), placeholder='开放平台ACCESS_KEY_SECRET').style("width:300px;")
                            input_bilibili_open_live_APP_ID = ui.input(label='项目ID', value=config.get("bilibili", "open_live", "APP_ID"), placeholder='开放平台 创作者服务中心 项目ID').style("width:200px;")
                            input_bilibili_open_live_ROOM_OWNER_AUTH_CODE = ui.input(label='身份码', value=config.get("bilibili", "open_live", "ROOM_OWNER_AUTH_CODE"), placeholder='直播中心用户 身份码').style("width:200px;")
            with ui.card().style(card_css):
                ui.label('twitch')
                with ui.row():
                    input_twitch_token = ui.input(label='Token', value=config.get("twitch", "token"), placeholder='Access https://twitchapps.com/tmi/ to get, format is: oauth:xxx').style("width:300px;")
                    input_twitch_user = ui.input(label='Username', value=config.get("twitch", "user"), placeholder='Your Twitch account username').style("width:300px;")
                    input_twitch_proxy_server = ui.input(label='HTTP Proxy IP Address', value=config.get("twitch", "proxy_server"), placeholder='Proxy software, IP address that http protocol listens to, usually: 127.0.0.1').style("width:200px;")
                    input_twitch_proxy_port = ui.input(label='HTTP Proxy Port', value=config.get("twitch", "proxy_port"), placeholder='Proxy software, port that http protocol listens to, usually: 1080').style("width:200px;")
                            
            with ui.card().style(card_css):
                ui.label('Audio Playback')
                with ui.row():
                    switch_play_audio_enable = ui.switch('Enable', value=config.get("play_audio", "enable")).style(switch_internal_css)
                    switch_play_audio_text_split_enable = ui.switch('Enable Text Splitting', value=config.get("play_audio", "text_split_enable")).style(switch_internal_css)
                    input_play_audio_normal_interval = ui.input(label='Normal Audio Playback Interval', value=config.get("play_audio", "normal_interval"), placeholder='The interval between the end of playing normal audio, such as danmaku replies or singing, and playing the next audio, in seconds')
                    input_play_audio_out_path = ui.input(label='Audio Output Path', placeholder='Path where the audio file is stored after synthesis, supports relative or absolute path', value=config.get("play_audio", "out_path"))
                    select_play_audio_player = ui.select(
                        label='Player',
                        options={'pygame': 'pygame', 'audio_player': 'audio_player'},
                        value=config.get("play_audio", "player")
                    ).style("width:200px")

            with ui.card().style(card_css):
                ui.label('audio_player')
                with ui.row():
                    input_audio_player_api_ip_port = ui.input(label='API地址', value=config.get("audio_player", "api_ip_port"), placeholder='audio_player的API地址，只需要 http://ip:端口 即可').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Read Danmaku')
                with ui.grid(columns=3):
                    switch_read_comment_enable = ui.switch('Enable', value=config.get("read_comment", "enable")).style(switch_internal_css)
                    switch_read_comment_read_username_enable = ui.switch('Read Username', value=config.get("read_comment", "read_username_enable")).style(switch_internal_css)
                    input_read_comment_username_max_len = ui.input(label='Maximum Username Length', value=config.get("read_comment", "username_max_len"), placeholder='Maximum length of the username to retain, excess will be discarded').style("width:100px;") 
                    switch_read_comment_voice_change = ui.switch('Voice Change', value=config.get("read_comment", "voice_change")).style(switch_internal_css)
                with ui.grid(columns=2):
                    textarea_read_comment_read_username_copywriting = ui.textarea(label='Read Username Copywriting', placeholder='Copywriting used when reading usernames, you can customize and edit multiple (separated by line breaks), one will be randomly selected in practice', value=textarea_data_change(config.get("read_comment", "read_username_copywriting"))).style("width:500px;")
            with ui.card().style(card_css):
                ui.label('Read User Name When Replying')
                with ui.grid(columns=2):
                    switch_read_user_name_enable = ui.switch('Enable', value=config.get("read_user_name", "enable")).style(switch_internal_css)
                    input_read_user_name_username_max_len = ui.input(label='Maximum Username Length', value=config.get("read_user_name", "username_max_len"), placeholder='Maximum length of the username to retain, excess will be discarded').style("width:100px;") 
                    switch_read_user_name_voice_change = ui.switch('Enable Voice Change', value=config.get("read_user_name", "voice_change")).style(switch_internal_css)
                with ui.grid(columns=2):
                    textarea_read_user_name_reply_before = ui.textarea(label='Pre-reply', placeholder='Copywriting used when reading usernames before a serious reply, currently triggered by local Q&A library - text', value=textarea_data_change(config.get("read_user_name", "reply_before"))).style("width:500px;")
                    textarea_read_user_name_reply_after = ui.textarea(label='Post-reply', placeholder='Copywriting used when reading usernames after a serious reply, currently triggered by local Q&A library - audio', value=textarea_data_change(config.get("read_user_name", "reply_after"))).style("width:500px;")
            with ui.card().style(card_css):
                ui.label('Logs')
                with ui.grid(columns=3):
                    switch_captions_enable = ui.switch('Enable', value=config.get("captions", "enable")).style(switch_internal_css)

                    select_comment_log_type = ui.select(
                        label='弹幕日志类型',
                        options={'Q&A': 'Q&A', 'Question': 'Question', 'Answer': 'Answer', 'Do Not Record': 'Do Not Record'},
                        value=config.get("comment_log_type")
                    )
                    input_captions_file_path = ui.input(label='Subtitle log path', placeholder='Subtitle log storage path', value=config.get("captions", "file_path")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label('Local Q&A')
                with ui.grid(columns=4):
                    switch_local_qa_text_enable = ui.switch('启用文本匹配', value=config.get("local_qa", "text", "enable")).style(switch_internal_css)
                    select_local_qa_text_type = ui.select(
                        label='弹幕日志类型',
                        options={'json': '自定义json', 'text': '一问一答'},
                        value=config.get("local_qa", "text", "type")
                    )
                    input_local_qa_text_file_path = ui.input(label='Text Q&A Data Path', placeholder='Path to local text Q&A data', value=config.get("local_qa", "text", "file_path")).style("width:200px;")
                    input_local_qa_text_similarity = ui.input(label='Text Minimum Similarity', placeholder='Minimum similarity for text matching, i.e., the minimum similarity between user-sent content and locally set content.\nLow values treat the danmaku as general comments.', value=config.get("local_qa", "text", "similarity")).style("width:200px;")
                with ui.grid(columns=4):
                    switch_local_qa_audio_enable = ui.switch('Enable Audio Matching', value=config.get("local_qa", "audio", "enable")).style(switch_internal_css)
                    input_local_qa_audio_file_path = ui.input(label='Audio Storage Path', placeholder='Path to local audio Q&A data', value=config.get("local_qa", "audio", "file_path")).style("width:200px;")
                    input_local_qa_audio_similarity = ui.input(label='Audio Minimum Similarity', placeholder='Minimum similarity for audio matching, i.e., the minimum similarity between user-sent content and locally set audio filenames.\nLow values treat the danmaku as general comments.', value=config.get("local_qa", "audio", "similarity")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label('Filter')
                with ui.grid(columns=4):
                    textarea_filter_before_must_str = ui.textarea(label='Danmaku Trigger Prefix', placeholder='Danmaku must carry any of these strings as a prefix to trigger.\nFor example, configuring # would trigger this: #Hello', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:300px;")
                    textarea_filter_after_must_str = ui.textarea(label='Danmaku Trigger Suffix', placeholder='Danmaku must carry any of these strings as a suffix to trigger.\nFor example, configuring . would trigger this: Hello.', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:300px;")
                    textarea_filter_before_filter_str = ui.textarea(label='Danmaku Filter Prefix', placeholder='Danmaku will be filtered when the prefix is any of these strings.\nFor example, configuring # would filter this: #Hello', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:300px;")
                    textarea_filter_after_filter_str = ui.textarea(label='Danmaku Filter Suffix', placeholder='Danmaku will be filtered when the suffix is any of these strings.\nFor example, configuring # would filter this: Hello#', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:300px;")
                with ui.grid(columns=4):
                    input_filter_badwords_path = ui.input(label='Profanity Path', placeholder='Path to local profanity data (If not needed, you can clear the file content)', value=config.get("filter", "badwords_path")).style("width:200px;")
                    input_filter_bad_pinyin_path = ui.input(label='Profanity Pinyin Path', placeholder='Path to local profanity pinyin data (If not needed, you can clear the file content)', value=config.get("filter", "bad_pinyin_path")).style("width:200px;")
                    input_filter_max_len = ui.input(label='Max Word Count', placeholder='Maximum number of English words to read (separated by spaces)', value=config.get("filter", "max_len")).style("width:200px;")
                    input_filter_max_char_len = ui.input(label='Max Character Count', placeholder='Maximum number of characters to read, double-filtered to avoid overflow', value=config.get("filter", "max_char_len")).style("width:200px;")
                with ui.grid(columns=4):
                    input_filter_comment_forget_duration = ui.input(label='Danmaku Forget Interval', placeholder='This is the interval (in seconds) to discard the received data every interval,\nand the reserved data can be customized in the following configuration', value=config.get("filter", "comment_forget_duration")).style("width:200px;")
                    input_filter_comment_forget_reserve_num = ui.input(label='Danmaku Reserved Number', placeholder='Number of the latest received data to be reserved', value=config.get("filter", "comment_forget_reserve_num")).style("width:200px;")
                    input_filter_gift_forget_duration = ui.input(label='Gift Forget Interval', placeholder='This is the interval (in seconds) to discard the received data every interval,\nand the reserved data can be customized in the following configuration', value=config.get("filter", "gift_forget_duration")).style("width:200px;")
                    input_filter_gift_forget_reserve_num = ui.input(label='Gift Reserved Number', placeholder='Number of the latest received data to be reserved', value=config.get("filter", "gift_forget_reserve_num")).style("width:200px;")
                with ui.grid(columns=4):
                    input_filter_entrance_forget_duration = ui.input(label='Entrance Forget Interval', placeholder='This is the interval (in seconds) to discard the received data every interval,\nand the reserved data can be customized in the following configuration', value=config.get("filter", "entrance_forget_duration")).style("width:200px;")
                    input_filter_entrance_forget_reserve_num = ui.input(label='Entrance Reserved Number', placeholder='Number of the latest received data to be reserved', value=config.get("filter", "entrance_forget_reserve_num")).style("width:200px;")
                    input_filter_follow_forget_duration = ui.input(label='Follow Forget Interval', placeholder='This is the interval (in seconds) to discard the received data every interval,\nand the reserved data can be customized in the following configuration', value=config.get("filter", "follow_forget_duration")).style("width:200px;")
                    input_filter_follow_forget_reserve_num = ui.input(label='Follow Reserved Number', placeholder='Number of the latest received data to be reserved', value=config.get("filter", "follow_forget_reserve_num")).style("width:200px;")
                with ui.grid(columns=4):
                    input_filter_talk_forget_duration = ui.input(label='Talk Forget Interval', placeholder='This is the interval (in seconds) to discard the received data every interval,\nand the reserved data can be customized in the following configuration', value=config.get("filter", "talk_forget_duration")).style("width:200px;")
                    input_filter_talk_forget_reserve_num = ui.input(label='Talk Reserved Number', placeholder='Number of the latest received data to be reserved', value=config.get("filter", "talk_forget_reserve_num")).style("width:200px;")
                    input_filter_schedule_forget_duration = ui.input(label='Schedule Forget Interval', placeholder='This is the interval (in seconds) to discard the received data every interval,\nand the reserved data can be customized in the following configuration', value=config.get("filter", "schedule_forget_duration")).style("width:200px;")
                    input_filter_schedule_forget_reserve_num = ui.input(label='Schedule Reserved Number', placeholder='Number of the latest received data to be reserved', value=config.get("filter", "schedule_forget_reserve_num")).style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Acknowledgments')
                with ui.row():
                    input_thanks_username_max_len = ui.input(label='Maximum Username Length', value=config.get("thanks", "username_max_len"), placeholder='Maximum length to retain for the username; excess will be discarded').style("width:100px;")
                with ui.row():
                    switch_thanks_entrance_enable = ui.switch('Enable Entrance Greetings', value=config.get("thanks", "entrance_enable")).style(switch_internal_css)
                    switch_thanks_entrance_random = ui.switch('Random Selection', value=config.get("thanks", "entrance_random")).style(switch_internal_css)
                    textarea_thanks_entrance_copy = ui.textarea(label='Entrance Copy', value=textarea_data_change(config.get("thanks", "entrance_copy")), placeholder='Related copy for user entry; do not modify {username}, as this string is used to replace the username').style("width:500px;")
                with ui.row():
                    switch_thanks_gift_enable = ui.switch('Enable Gift Acknowledgments', value=config.get("thanks", "gift_enable")).style(switch_internal_css)
                    switch_thanks_gift_random = ui.switch('Random Selection', value=config.get("thanks", "gift_random")).style(switch_internal_css)
                    textarea_thanks_gift_copy = ui.textarea(label='Gift Copy', value=textarea_data_change(config.get("thanks", "gift_copy")), placeholder='Related copy for user gift giving; do not modify {username} and {gift_name}, as these strings are used to replace the username and gift name').style("width:500px;")
                    input_thanks_lowest_price = ui.input(label='Minimum Thanks Gift Price', value=config.get("thanks", "lowest_price"), placeholder='Set the minimum price (in yuan) for thanks-giving gifts; gifts below this value will not trigger acknowledgments').style("width:100px;")
                with ui.row():
                    switch_thanks_follow_enable = ui.switch('Enable Follow Acknowledgments', value=config.get("thanks", "follow_enable")).style(switch_internal_css)
                    switch_thanks_follow_random = ui.switch('Random Selection', value=config.get("thanks", "follow_random")).style(switch_internal_css)
                    textarea_thanks_follow_copy = ui.textarea(label='Follow Copy', value=textarea_data_change(config.get("thanks", "follow_copy")), placeholder='Related copy for user follow; do not modify {username}, as this string is used to replace the username').style("width:500px;")

            with ui.card().style(card_css):
                ui.label('Random Audio Speed')
                with ui.grid(columns=3):
                    switch_audio_random_speed_normal_enable = ui.switch('Normal Speed', value=config.get("audio_random_speed", "normal", "enable")).style(switch_internal_css)
                    input_audio_random_speed_normal_speed_min = ui.input(label='Minimum Speed', value=config.get("audio_random_speed", "normal", "speed_min")).style("width:200px;")
                    input_audio_random_speed_normal_speed_max = ui.input(label='Maximum Speed', value=config.get("audio_random_speed", "normal", "speed_max")).style("width:200px;")
                with ui.grid(columns=3):
                    switch_audio_random_speed_copywriting_enable = ui.switch('Copywriting Speed', value=config.get("audio_random_speed", "copywriting", "enable")).style(switch_internal_css)
                    input_audio_random_speed_copywriting_speed_min = ui.input(label='Minimum Speed', value=config.get("audio_random_speed", "copywriting", "speed_min")).style("width:200px;")
                    input_audio_random_speed_copywriting_speed_max = ui.input(label='Maximum Speed', value=config.get("audio_random_speed", "copywriting", "speed_max")).style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Live2D') 
                with ui.grid(columns=2):
                    switch_live2d_enable = ui.switch('Enable', value=config.get("live2d", "enable")).style(switch_internal_css)
                    input_live2d_port = ui.input(label='Port', value=config.get("live2d", "port")).style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Song Mode') 
                with ui.row():
                    switch_choose_song_enable = ui.switch('Enable', value=config.get("choose_song", "enable")).style(switch_internal_css)
                    textarea_choose_song_start_cmd = ui.textarea(label='Start Command', value=textarea_data_change(config.get("choose_song", "start_cmd")), placeholder='Start command, separated by line breaks, supports multiple commands, triggered by barrage sending (must be a complete match)').style("width:200px;")
                    textarea_choose_song_stop_cmd = ui.textarea(label='Stop Command', value=textarea_data_change(config.get("choose_song", "stop_cmd")), placeholder='Stop command, separated by line breaks, supports multiple commands, triggered by barrage sending (must be a complete match)').style("width:200px;")
                    textarea_choose_song_random_cmd = ui.textarea(label='Random Command', value=textarea_data_change(config.get("choose_song", "random_cmd")), placeholder='Random command, separated by line breaks, supports multiple commands, triggered by barrage sending (must be a complete match)').style("width:200px;")
                with ui.row():
                    input_choose_song_song_path = ui.input(label='Song Path', value=config.get("choose_song", "song_path"), placeholder='Path where the song audio is stored, will automatically read the audio files').style("width:200px;")
                    input_choose_song_match_fail_copy = ui.input(label='Match Failure Copy', value=config.get("choose_song", "match_fail_copy"), placeholder='Return audio copy when matching fails. Note: {content} is used to replace the song name sent by the user, do not delete it randomly! It will affect usage!').style("width:300px;")
                    input_choose_song_similarity = ui.input(label='Minimum Match Similarity', value=config.get("choose_song", "similarity"), placeholder='Minimum audio match similarity, i.e. the lowest similarity between the content sent by the user and the file name of the audio file in the local audio library.\nIf it is low, it will be treated as a normal barrage').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Scheduled Tasks')
                schedule_var = {}
                for index, schedule in enumerate(config.get("schedule")):
                    with ui.row():
                        schedule_var[str(3 * index)] = ui.switch(text=f"Enable Task {index}", value=schedule["enable"]).style(switch_internal_css)
                        schedule_var[str(3 * index + 1)] = ui.input(label="Cycle Period", value=schedule["time"], placeholder='The cycle duration of the scheduled task (in seconds), i.e. it will be executed once every interval of this duration').style("width:200px;")
                        schedule_var[str(3 * index + 2)] = ui.textarea(label="Copy List", value=textarea_data_change(schedule["copy"]), placeholder='List of copies, separated by spaces or line breaks, use {variables} to replace key data, custom functions can be modified in the source code').style("width:500px;")

            with ui.card().style(card_css):
                ui.label('Idle Time Tasks')
                with ui.row():
                    switch_idle_time_task_enable = ui.switch('Enable', value=config.get("idle_time_task", "enable")).style(switch_internal_css)
                    input_idle_time_task_idle_time = ui.input(label='Idle Time', value=config.get("idle_time_task", "idle_time"), placeholder='Time interval during idle time (positive integer, unit: seconds), i.e. the time that has passed without barrage situations').style("width:200px;")
                    switch_idle_time_task_random_time = ui.switch('Random Idle Time', value=config.get("idle_time_task", "random_time")).style(switch_internal_css)
                with ui.row():
                    switch_idle_time_task_comment_enable = ui.switch('LLM Mode', value=config.get("idle_time_task", "comment", "enable")).style(switch_internal_css)
                    switch_idle_time_task_comment_random = ui.switch('Random Copy', value=config.get("idle_time_task", "comment", "random")).style(switch_internal_css)
                    textarea_idle_time_task_comment_copy = ui.textarea(label='Copy List', value=textarea_data_change(config.get("idle_time_task", "comment", "copy")), placeholder='List of copies, separated by line breaks, the copies will be processed by LLM and directly synthesized into the result').style("width:800px;")
                with ui.row():
                    switch_idle_time_task_local_audio_enable = ui.switch('Local Audio Mode', value=config.get("idle_time_task", "local_audio", "enable")).style(switch_internal_css)
                    switch_idle_time_task_local_audio_random = ui.switch('Random Local Audio', value=config.get("idle_time_task", "local_audio", "random")).style(switch_internal_css)
                    textarea_idle_time_task_local_audio_path = ui.textarea(label='Local Audio Path List', value=textarea_data_change(config.get("idle_time_task", "local_audio", "path")), placeholder='List of local audio paths, separated by line breaks between relative/absolute paths, the audio files will be directly added to the audio playback queue').style("width:800px;")
                        
            with ui.card().style(card_css):
                ui.label('Stable Diffusion')
                with ui.grid(columns=2):
                    switch_sd_enable = ui.switch('Enable', value=config.get("sd", "enable")).style(switch_internal_css)
                with ui.grid(columns=3):    
                    select_sd_prompt_llm_type = ui.select(
                        label='LLM Type',
                        options={
                            'chatgpt': 'ChatGPT/WenDa', 
                            'claude': 'Claude', 
                            'claude2': 'Claude2',
                            'chatglm': 'ChatGLM',
                            'chat_with_file': 'Chat with File',
                            'chatterbot': 'Chatterbot',
                            'text_generation_webui': 'Text Generation WebUI',
                            'sparkdesk': 'Xunfei Xinghuo',
                            'langchain_chatglm': 'LangChain ChatGLM',
                            'langchain_chatchat': 'LangChain ChatChat',
                            # 'zhipu': 'Zhipu AI',
                            'bard': 'Bard',
                            # 'yiyan': 'Wenxin Yiyuan',
                            # 'tongyixingchen': 'Tongyi Xingchen',
                            # 'my_wenxinworkshop': 'Qianfan Da Model',
                            'gemini': 'Gemini',
                            "none": "Disable"
                        },
                        value=config.get("sd", "prompt_llm", "type")
                    )
                    input_sd_prompt_llm_before_prompt = ui.input(label='Prompt Prefix', value=config.get("sd", "prompt_llm", "before_prompt"), placeholder='LLM prompt prefix').style("width:200px;")
                    input_sd_prompt_llm_after_prompt = ui.input(label='Prompt Suffix', value=config.get("sd", "prompt_llm", "after_prompt"), placeholder='LLM prompt suffix').style("width:200px;")
                with ui.grid(columns=3): 
                    input_sd_trigger = ui.input(label='Danmaku Trigger Prefix', value=config.get("sd", "trigger"), placeholder='Keywords triggering danmaku (at the beginning)').style("width:200px;")
                    input_sd_ip = ui.input(label='IP Address', value=config.get("sd", "ip"), placeholder='IP address where the service is running').style("width:200px;")
                    input_sd_port = ui.input(label='Port', value=config.get("sd", "port"), placeholder='Port where the service is running').style("width:200px;")
                with ui.grid(columns=3):
                    input_sd_negative_prompt = ui.input(label='Negative Prompt', value=config.get("sd", "negative_prompt"), placeholder='Negative text prompt, used to specify content contradictory or opposite to the generated image').style("width:200px;")
                    input_sd_seed = ui.input(label='Random Seed', value=config.get("sd", "seed"), placeholder='Random seed used to control randomness in the generation process. You can set an integer value for reproducible results.').style("width:200px;")
                    textarea_sd_styles = ui.textarea(label='Image Styles', placeholder='Style list used to specify the styles of the generated image. It can include multiple styles, such as ["anime", "portrait"]', value=textarea_data_change(config.get("sd", "styles"))).style("width:200px;")
                with ui.grid(columns=2):
                    input_sd_cfg_scale = ui.input(label='Prompt Relevance', value=config.get("sd", "cfg_scale"), placeholder='Prompt relevance; scale of influence when there is no classifier guidance (Classifier Free Guidance Scale) - To what extent the generated image should follow the prompt - Lower values produce more creative results.').style("width:200px;")
                    input_sd_steps = ui.input(label='Number of Image Generation Steps', value=config.get("sd", "steps"), placeholder='Number of steps for generating the image; used to control the precision of the generation.').style("width:200px;")
                with ui.grid(columns=3):    
                    input_sd_hr_resize_x = ui.input(label='Image Horizontal Pixels', value=config.get("sd", "hr_resize_x"), placeholder='Horizontal size of the generated image.').style("width:200px;")
                    input_sd_hr_resize_y = ui.input(label='Image Vertical Pixels', value=config.get("sd", "hr_resize_y"), placeholder='Vertical size of the generated image.').style("width:200px;")
                    input_sd_denoising_strength = ui.input(label='Denoising Strength', value=config.get("sd", "denoising_strength"), placeholder='Denoising strength; used to control the noise in the generated image.').style("width:200px;")
                with ui.grid(columns=3):
                    switch_sd_enable_hr = ui.switch('High-Resolution Generation', value=config.get("sd", "enable_hr")).style(switch_internal_css)
                    input_sd_hr_scale = ui.input(label='High-Resolution Scaling Factor', value=config.get("sd", "hr_scale"), placeholder='Scaling factor for high-resolution generation; specifies the high-resolution scaling level of the generated image.').style("width:200px;")
                    input_sd_hr_second_pass_steps = ui.input(label='High-Resolution Second Pass Steps', value=config.get("sd", "hr_second_pass_steps"), placeholder='Number of steps for the second pass of high-resolution generation.').style("width:200px;")
                    
            with ui.card().style(card_css):
                ui.label('Dynamic Copywriting')
                with ui.grid(columns=3):
                    switch_trends_copywriting_enable = ui.switch('Enable', value=config.get("trends_copywriting", "enable")).style(switch_internal_css)
                    switch_trends_copywriting_random_play = ui.switch('Random Play', value=config.get("trends_copywriting", "random_play")).style(switch_internal_css)
                    input_trends_copywriting_play_interval = ui.input(label='Copywriting Play Interval', value=config.get("trends_copywriting", "play_interval"), placeholder='Interval between the play of copywritings (in seconds)').style("width:200px;")
                trends_copywriting_copywriting_var = {}
                for index, trends_copywriting_copywriting in enumerate(config.get("trends_copywriting", "copywriting")):
                    with ui.grid(columns=3):
                        trends_copywriting_copywriting_var[str(3 * index)] = ui.input(label=f"Copywriting Path {index}", value=trends_copywriting_copywriting["folder_path"], placeholder='Folder path where copywriting files are stored').style("width:200px;")
                        trends_copywriting_copywriting_var[str(3 * index + 1)] = ui.switch(text="Prompt Conversion", value=trends_copywriting_copywriting["prompt_change_enable"])
                        trends_copywriting_copywriting_var[str(3 * index + 2)] = ui.input(label="Prompt Conversion Content", value=trends_copywriting_copywriting["prompt_change_content"], placeholder='Convert the copywriting content using this prompt content before synthesis; LLM used is configured for chat type').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Web Captions Printer')
                with ui.grid(columns=2):
                    switch_web_captions_printer_enable = ui.switch('Enable', value=config.get("web_captions_printer", "enable")).style(switch_internal_css)
                    input_web_captions_printer_api_ip_port = ui.input(label='API Address', value=config.get("web_captions_printer", "api_ip_port"), placeholder='API address of the web captions printer, just need http://ip:port').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Database')
                with ui.grid(columns=4):
                    switch_database_comment_enable = ui.switch('Danmaku Logs', value=config.get("database", "comment_enable")).style(switch_internal_css)
                    switch_database_entrance_enable = ui.switch('Entrance Logs', value=config.get("database", "entrance_enable")).style(switch_internal_css)
                    switch_database_gift_enable = ui.switch('Gift Logs', value=config.get("database", "gift_enable")).style(switch_internal_css)
                    input_database_path = ui.input(label='Database Path', value=config.get("database", "path"), placeholder='Path to the database file').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Key Mapping')
                with ui.row():
                    switch_key_mapping_enable = ui.switch('Enable', value=config.get("key_mapping", "enable")).style(switch_internal_css)
                    select_key_mapping_type = ui.select(
                        label='Type',
                        options={'Danmaku': 'Danmaku', 'Reply': 'Reply', 'Danmaku+Reply': 'Danmaku+Reply'},
                        value=config.get("key_mapping", "type")
                    ).style("width:300px")
                    input_key_mapping_start_cmd = ui.input(label='Command Prefix', value=config.get("key_mapping", "start_cmd"), placeholder='To trigger this function, the command must start with this string, otherwise it will not be parsed as a key mapping command').style("width:200px;")

                key_mapping_config_var = {}
                for index, key_mapping_config in enumerate(config.get("key_mapping", "config")):
                    with ui.grid(columns=3):
                        key_mapping_config_var[str(3 * index)] = ui.textarea(label="Keywords", value=textarea_data_change(key_mapping_config["keywords"]), placeholder='Enter the triggering keywords here').style("width:200px;")
                        key_mapping_config_var[str(3 * index + 1)] = ui.textarea(label="Keys", value=textarea_data_change(key_mapping_config["keys"]), placeholder='Enter the keys you want to map, separate multiple keys with line breaks (reference pyautogui rules)').style("width:200px;")
                        key_mapping_config_var[str(3 * index + 2)] = ui.input(label="Similarity", value=key_mapping_config["similarity"], placeholder='Similarity between keywords and user input, default is 1 (100%)').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Dynamic Configuration')
                with ui.row():
                    switch_trends_config_enable = ui.switch('Enable', value=config.get("trends_config", "enable")).style(switch_internal_css)

                trends_config_path_var = {}
                for index, trends_config_path in enumerate(config.get("trends_config", "path")):
                    with ui.grid(columns=2):
                        trends_config_path_var[str(2 * index)] = ui.input(label="Online User Range", value=trends_config_path["online_num"], placeholder='Online user range, separated by a hyphen "-", e.g., 0-10').style("width:200px;")
                        trends_config_path_var[str(2 * index + 1)] = ui.input(label="Configuration Path", value=trends_config_path["path"], placeholder='Enter the path of the loaded configuration file here').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Abnormal Alarm')
                with ui.row():
                    switch_abnormal_alarm_platform_enable = ui.switch('Enable Platform Alarm', value=config.get("abnormal_alarm", "platform", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_platform_type = ui.select(
                        label='Type',
                        options={'local_audio': 'Local Audio'},
                        value=config.get("abnormal_alarm", "platform", "type")
                    )
                    input_abnormal_alarm_platform_start_alarm_error_num = ui.input(label='Start Alarm Error Number', value=config.get("abnormal_alarm", "platform", "start_alarm_error_num"), placeholder='Number of errors to start the abnormal alarm, an alarm will be triggered after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_platform_auto_restart_error_num = ui.input(label='Auto Restart Error Number', value=config.get("abnormal_alarm", "platform", "auto_restart_error_num"), placeholder='Remember to enable the "Auto Run" function first. Number of errors for automatic restart of the web UI after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_platform_local_audio_path = ui.input(label='Local Audio Path', value=config.get("abnormal_alarm", "platform", "local_audio_path"), placeholder='File path where local audio is stored (can be multiple audio files, randomly selected)').style("width:300px;")

                with ui.row():
                    switch_abnormal_alarm_llm_enable = ui.switch('Enable LLM Alarm', value=config.get("abnormal_alarm", "llm", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_llm_type = ui.select(
                        label='Type',
                        options={'local_audio': 'Local Audio'},
                        value=config.get("abnormal_alarm", "llm", "type")
                    )
                    input_abnormal_alarm_llm_start_alarm_error_num = ui.input(label='Start Alarm Error Number', value=config.get("abnormal_alarm", "llm", "start_alarm_error_num"), placeholder='Number of errors to start the abnormal alarm, an alarm will be triggered after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_llm_auto_restart_error_num = ui.input(label='Auto Restart Error Number', value=config.get("abnormal_alarm", "llm", "auto_restart_error_num"), placeholder='Remember to enable the "Auto Run" function first. Number of errors for automatic restart of the web UI after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_llm_local_audio_path = ui.input(label='Local Audio Path', value=config.get("abnormal_alarm", "llm", "local_audio_path"), placeholder='File path where local audio is stored (can be multiple audio files, randomly selected)').style("width:300px;")

                with ui.row():
                    switch_abnormal_alarm_tts_enable = ui.switch('Enable TTS Alarm', value=config.get("abnormal_alarm", "tts", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_tts_type = ui.select(
                        label='Type',
                        options={'local_audio': 'Local Audio'},
                        value=config.get("abnormal_alarm", "tts", "type")
                    )
                    input_abnormal_alarm_tts_start_alarm_error_num = ui.input(label='Start Alarm Error Number', value=config.get("abnormal_alarm", "tts", "start_alarm_error_num"), placeholder='Number of errors to start the abnormal alarm, an alarm will be triggered after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_tts_auto_restart_error_num = ui.input(label='Auto Restart Error Number', value=config.get("abnormal_alarm", "tts", "auto_restart_error_num"), placeholder='Remember to enable the "Auto Run" function first. Number of errors for automatic restart of the web UI after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_tts_local_audio_path = ui.input(label='Local Audio Path', value=config.get("abnormal_alarm", "tts", "local_audio_path"), placeholder='File path where local audio is stored (can be multiple audio files, randomly selected)').style("width:300px;")

                with ui.row():
                    switch_abnormal_alarm_svc_enable = ui.switch('Enable SVC Alarm', value=config.get("abnormal_alarm", "svc", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_svc_type = ui.select(
                        label='Type',
                        options={'local_audio': 'Local Audio'},
                        value=config.get("abnormal_alarm", "svc", "type")
                    )
                    input_abnormal_alarm_svc_start_alarm_error_num = ui.input(label='Start Alarm Error Number', value=config.get("abnormal_alarm", "svc", "start_alarm_error_num"), placeholder='Number of errors to start the abnormal alarm, an alarm will be triggered after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_svc_auto_restart_error_num = ui.input(label='Auto Restart Error Number', value=config.get("abnormal_alarm", "svc", "auto_restart_error_num"), placeholder='Remember to enable the "Auto Run" function first. Number of errors for automatic restart of the web UI after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_svc_local_audio_path = ui.input(label='Local Audio Path', value=config.get("abnormal_alarm", "svc", "local_audio_path"), placeholder='File path where local audio is stored (can be multiple audio files, randomly selected)').style("width:300px;")

                with ui.row():
                    switch_abnormal_alarm_visual_body_enable = ui.switch('Enable Visual Body Alarm', value=config.get("abnormal_alarm", "visual_body", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_visual_body_type = ui.select(
                        label='Type',
                        options={'local_audio': 'Local Audio'},
                        value=config.get("abnormal_alarm", "visual_body", "type")
                    )
                    input_abnormal_alarm_visual_body_start_alarm_error_num = ui.input(label='Start Alarm Error Number', value=config.get("abnormal_alarm", "visual_body", "start_alarm_error_num"), placeholder='Number of errors to start the abnormal alarm, an alarm will be triggered after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_visual_body_auto_restart_error_num = ui.input(label='Auto Restart Error Number', value=config.get("abnormal_alarm", "visual_body", "auto_restart_error_num"), placeholder='Remember to enable the "Auto Run" function first. Number of errors for automatic restart of the web UI after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_visual_body_local_audio_path = ui.input(label='Local Audio Path', value=config.get("abnormal_alarm", "visual_body", "local_audio_path"), placeholder='File path where local audio is stored (can be multiple audio files, randomly selected)').style("width:300px;")

                with ui.row():
                    switch_abnormal_alarm_other_enable = ui.switch('Enable Other Alarm', value=config.get("abnormal_alarm", "other", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_other_type = ui.select(
                        label='Type',
                        options={'local_audio': 'Local Audio'},
                        value=config.get("abnormal_alarm", "other", "type")
                    )
                    input_abnormal_alarm_other_start_alarm_error_num = ui.input(label='Start Alarm Error Number', value=config.get("abnormal_alarm", "other", "start_alarm_error_num"), placeholder='Number of errors to start the abnormal alarm, an alarm will be triggered after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_other_auto_restart_error_num = ui.input(label='Auto Restart Error Number', value=config.get("abnormal_alarm", "other", "auto_restart_error_num"), placeholder='Remember to enable the "Auto Run" function first. Number of errors for automatic restart of the web UI after exceeding this number').style("width:100px;")
                    input_abnormal_alarm_other_local_audio_path = ui.input(label='Local Audio Path', value=config.get("abnormal_alarm", "other", "local_audio_path"), placeholder='File path where local audio is stored (can be multiple audio files, randomly selected)').style("width:300px;")
                    
        with ui.tab_panel(llm_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("ChatGPT/WenDa")
                with ui.row():
                    input_openai_api = ui.input(label='API Address', placeholder='API request address, supports proxy', value=config.get("openai", "api")).style("width:200px;")
                    textarea_openai_api_key = ui.textarea(label='API Key', placeholder='API KEY, supports proxy', value=textarea_data_change(config.get("openai", "api_key"))).style("width:400px;")
                with ui.row():
                    chatgpt_models = ["gpt-3.5-turbo",
                        "gpt-3.5-turbo-0301",
                        "gpt-3.5-turbo-0613",
                        "gpt-3.5-turbo-1106",
                        "gpt-3.5-turbo-16k",
                        "gpt-3.5-turbo-16k-0613",
                        "gpt-3.5-turbo-instruct",
                        "gpt-3.5-turbo-instruct-0914",
                        "gpt-4",
                        "gpt-4-0314",
                        "gpt-4-0613",
                        "gpt-4-32k",
                        "gpt-4-32k-0314",
                        "gpt-4-32k-0613",
                        "gpt-4-1106-preview",
                        "text-embedding-ada-002",
                        "text-davinci-003",
                        "text-davinci-002",
                        "text-curie-001",
                        "text-babbage-001",
                        "text-ada-001",
                        "text-moderation-latest",
                        "text-moderation-stable",
                        "rwkv",
                        "chatglm3-6b"]
                    data_json = {}
                    for line in chatgpt_models:
                        data_json[line] = line
                    select_chatgpt_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("chatgpt", "model")
                    )
                    input_chatgpt_temperature = ui.input(label='Temperature', placeholder='Controls the randomness of generated text. Higher values make the text more random and diverse, while lower values make it more consistent.', value=config.get("chatgpt", "temperature")).style("width:200px;")
                    input_chatgpt_max_tokens = ui.input(label='Max Tokens', placeholder='Limits the maximum length of generated answers.', value=config.get("chatgpt", "max_tokens")).style("width:200px;")
                    input_chatgpt_top_p = ui.input(label='Top P', placeholder='Nucleus sampling. Controls the sampling from tokens with cumulative probability above a certain threshold.', value=config.get("chatgpt", "top_p")).style("width:200px;")
                with ui.row():
                    input_chatgpt_presence_penalty = ui.input(label='Presence Penalty', placeholder='Controls the attention to the given prompt when generating answers. Higher values reduce repetition and encourage more independent generation of answers.', value=config.get("chatgpt", "presence_penalty")).style("width:200px;")
                    input_chatgpt_frequency_penalty = ui.input(label='Frequency Penalty', placeholder='Controls the penalty for tokens that have already appeared in the generated answers. Higher values reduce the generation of frequently occurring tokens to avoid repetition.', value=config.get("chatgpt", "frequency_penalty")).style("width:200px;")
                    input_chatgpt_preset = ui.input(label='Preset', placeholder='Used to specify a set of predefined settings for better adaptation of the model to specific conversation scenarios.', value=config.get("chatgpt", "preset")).style("width:500px")
            with ui.card().style(card_css):
                ui.label("Claude")
                with ui.row():
                    input_claude_slack_user_token = ui.input(label='Slack User Token', placeholder='User Token configured in Slack platform, refer to the Claude section in the documentation for configuration', value=config.get("claude", "slack_user_token"))
                    input_claude_slack_user_token.style("width:400px")
                    input_claude_bot_user_id = ui.input(label='Bot User ID', placeholder='Member ID displayed by Claude added to Slack platform, refer to the Claude section in the documentation for configuration', value=config.get("claude", "bot_user_id"))
                    input_claude_bot_user_id.style("width:400px")
            with ui.card().style(card_css):
                ui.label("Claude2")
                with ui.row():
                    input_claude2_cookie = ui.input(label='Cookie', placeholder='claude.ai official website, open F12, capture a packet by asking any question, configure the request header cookie here', value=config.get("claude2", "cookie"))
                    input_claude2_cookie.style("width:400px")
                    switch_claude2_use_proxy = ui.switch('Enable Proxy', value=config.get("claude2", "use_proxy")).style(switch_internal_css)
                with ui.row():
                    input_claude2_proxies_http = ui.input(label='Proxies HTTP', placeholder='HTTP proxy address, default is http://127.0.0.1:10809', value=config.get("claude2", "proxies", "http"))
                    input_claude2_proxies_http.style("width:400px")
                    input_claude2_proxies_https = ui.input(label='Proxies HTTPS', placeholder='HTTPS proxy address, default is http://127.0.0.1:10809', value=config.get("claude2", "proxies", "https"))
                    input_claude2_proxies_https.style("width:400px")
                    input_claude2_proxies_socks5 = ui.input(label='Proxies SOCKS5', placeholder='SOCKS5 proxy address, default is socks://127.0.0.1:10808', value=config.get("claude2", "proxies", "socks5"))
                    input_claude2_proxies_socks5.style("width:400px")
            with ui.card().style(card_css):
                ui.label("ChatGLM")
                with ui.row():
                    input_chatglm_api_ip_port = ui.input(label='API Address', placeholder='Service link after running the API version of ChatGLM (needs complete URL)', value=config.get("chatglm", "api_ip_port"))
                    input_chatglm_api_ip_port.style("width:400px")
                    input_chatglm_max_length = ui.input(label='Max Length Limit', placeholder='Maximum length limit for generated answers, in terms of token or character count.', value=config.get("chatglm", "max_length"))
                    input_chatglm_max_length.style("width:200px")
                    input_chatglm_top_p = ui.input(label='Top P', placeholder='Also known as Nucleus sampling. Controls the threshold range of the probability selection when generating text.', value=config.get("chatglm", "top_p"))
                    input_chatglm_top_p.style("width:200px")
                    input_chatglm_temperature = ui.input(label='Temperature', placeholder='Temperature parameter, controls the randomness of generated text. Higher values produce more randomness and diversity in the text.', value=config.get("chatglm", "temperature"))
                    input_chatglm_temperature.style("width:200px")
                with ui.row():
                    switch_chatglm_history_enable = ui.switch('Context Memory', value=config.get("chatglm", "history_enable")).style(switch_internal_css)
                    input_chatglm_history_max_len = ui.input(label='Max Memory Length', placeholder='Maximum number of context characters to remember, not recommended to set too large, may cause GPU memory explosion, configure according to the situation', value=config.get("chatglm", "history_max_len"))
                    input_chatglm_history_max_len.style("width:200px")
            with ui.card().style(card_css):
                ui.label("Chat with File")
                with ui.row():
                    lines = ["claude", "openai_gpt", "openai_vector_search"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_chat_with_file_chat_mode = ui.select(
                        label='聊天模式', 
                        options=data_json, 
                        value=config.get("chat_with_file", "chat_mode")
                    )
                    input_chat_with_file_data_path = ui.input(label='Data File Path', placeholder='Local zip data file path to load (to x.zip), e.g., ./data/Icarus_Baidu_Baike.zip', value=config.get("chat_with_file", "data_path"))
                    input_chat_with_file_data_path.style("width:400px")
                with ui.row():
                    input_chat_with_file_separator = ui.input(label='Separator', placeholder='Separator for splitting text, use newline as the separator here.', value=config.get("chat_with_file", "separator"))
                    input_chat_with_file_separator.style("width:300px")
                    input_chat_with_file_chunk_size = ui.input(label='Chunk Size', placeholder='Maximum number of characters for each text chunk (the more characters in a text chunk, the more tokens are consumed, and the more detailed the response).', value=config.get("chat_with_file", "chunk_size"))
                    input_chat_with_file_chunk_size.style("width:300px")
                    input_chat_with_file_chunk_overlap = ui.input(label='Chunk Overlap', placeholder='Number of overlapping characters between two adjacent text chunks. This overlap helps maintain the coherence of the text, especially when the text is used for training language models or other machine learning models that require context information.', value=config.get("chat_with_file", "chunk_overlap"))
                    input_chat_with_file_chunk_overlap.style("width:300px")
                    lines = ["sebastian-hofstaetter/distilbert-dot-tas_b-b256-msmarco", "GanymedeNil/text2vec-large-chinese"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_chat_with_file_local_vector_embedding_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("chat_with_file", "local_vector_embedding_model")
                    )
                with ui.row():
                    input_chat_with_file_chain_type = ui.input(label='Chain Type', placeholder='Specify the type of language chain to be generated, e.g., stuff', value=config.get("chat_with_file", "chain_type"))
                    input_chat_with_file_chain_type.style("width:300px")
                    input_chat_with_file_question_prompt = ui.input(label='Question Summary Prompt', placeholder='Prompt words for summarizing the output of the local vector database through LLM, fill in the summary prompt words here', value=config.get("chat_with_file", "question_prompt"))
                    input_chat_with_file_question_prompt.style("width:300px")
                    input_chat_with_file_local_max_query = ui.input(label='Max Query Database Times', placeholder='Maximum number of queries to the database. Limiting the number of times helps save tokens.', value=config.get("chat_with_file", "local_max_query"))
                    input_chat_with_file_local_max_query.style("width:300px")
                    switch_chat_with_file_show_token_cost = ui.switch('Show Cost', value=config.get("chat_with_file", "show_token_cost")).style(switch_internal_css)
            with ui.card().style(card_css):
                ui.label("Chatterbot")
                with ui.grid(columns=2):
                    input_chatterbot_name = ui.input(label='Bot Name', placeholder='Bot name', value=config.get("chatterbot", "name"))
                    input_chatterbot_name.style("width:400px")
                    input_chatterbot_db_path = ui.input(label='Database Path', placeholder='Database path (absolute or relative path)', value=config.get("chatterbot", "db_path"))
                    input_chatterbot_db_path.style("width:400px")
            with ui.card().style(card_css):
                ui.label("text_generation_webui")
                with ui.row():
                    select_text_generation_webui_type = ui.select(
                        label='Type',
                        options={"Official API": "Official API", "coyude": "coyude"},
                        value=config.get("text_generation_webui", "type")
                    )
                    input_text_generation_webui_api_ip_port = ui.input(label='API Address', placeholder='IP and port address that text-generation-webui listens to when in API mode', value=config.get("text_generation_webui", "api_ip_port"))
                    input_text_generation_webui_api_ip_port.style("width:300px")
                    input_text_generation_webui_max_new_tokens = ui.input(label='max_new_tokens', placeholder='Refer to documentation', value=config.get("text_generation_webui", "max_new_tokens"))
                    input_text_generation_webui_max_new_tokens.style("width:200px")
                    switch_text_generation_webui_history_enable = ui.switch('Context Memory', value=config.get("text_generation_webui", "history_enable")).style(switch_internal_css)
                    input_text_generation_webui_history_max_len = ui.input(label='Max Memory Length', placeholder='Maximum number of characters for context memory, not recommended to set too large, may cause GPU memory explosion, configure according to the situation', value=config.get("text_generation_webui", "history_max_len"))
                    input_text_generation_webui_history_max_len.style("width:200px")
                with ui.row():
                    select_text_generation_webui_mode = ui.select(
                        label='Mode',
                        options={"chat": "chat", "chat-instruct": "chat-instruct", "instruct": "instruct"},
                        value=config.get("text_generation_webui", "mode")
                    ).style("width:150px")
                    input_text_generation_webui_character = ui.input(label='character', placeholder='Refer to documentation', value=config.get("text_generation_webui", "character"))
                    input_text_generation_webui_character.style("width:100px")
                    input_text_generation_webui_instruction_template = ui.input(label='instruction_template', placeholder='Refer to documentation', value=config.get("text_generation_webui", "instruction_template"))
                    input_text_generation_webui_instruction_template.style("width:150px")
                    input_text_generation_webui_your_name = ui.input(label='your_name', placeholder='Refer to documentation', value=config.get("text_generation_webui", "your_name"))
                    input_text_generation_webui_your_name.style("width:100px")
                with ui.row():
                    input_text_generation_webui_top_p = ui.input(label='top_p', value=config.get("text_generation_webui", "top_p"), placeholder='For topP generation, probability threshold for nucleus sampling method. For example, a value of 0.8 retains only tokens in the probability distribution with a cumulative probability greater than or equal to 0.8 as candidates for random sampling. The range is (0,1.0), the larger the value, the higher the randomness of the generation; the smaller the value, the lower the randomness of the generation. Default value is 0.95. Note that the value should not be greater than or equal to 1')
                    input_text_generation_webui_top_k = ui.input(label='top_k', value=config.get("text_generation_webui", "top_k"), placeholder='Number of matching search results')
                    input_text_generation_webui_temperature = ui.input(label='temperature', value=config.get("text_generation_webui", "temperature"), placeholder='Higher values make the output more random, while lower values make the output more focused and deterministic. Optional, default value is 0.92')
                    input_text_generation_webui_seed = ui.input(label='seed', value=config.get("text_generation_webui", "seed"), placeholder='For seed generation, the seed of the random number used to control the randomness of the model generation. If the same seed is used, the results generated each time will be the same; when you need to reproduce the generated results of the model, you can use the same seed. The seed parameter supports unsigned 64-bit integer type. Default value is 1683806810')

            with ui.card().style(card_css):
                ui.label("Xunfei SparkDesk")
                with ui.grid(columns=2):
                    lines = ["web", "api"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_sparkdesk_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("sparkdesk", "type")
                    )
                    input_sparkdesk_cookie = ui.input(label='Cookie', placeholder='Cookie from the web capture request header, refer to the documentation tutorial', value=config.get("sparkdesk", "cookie"))
                    input_sparkdesk_cookie.style("width:400px")
                with ui.row():
                    input_sparkdesk_fd = ui.input(label='FD', placeholder='FD from the web capture payload, refer to the documentation tutorial', value=config.get("sparkdesk", "fd"))
                    input_sparkdesk_fd.style("width:300px")
                    input_sparkdesk_GtToken = ui.input(label='GtToken', placeholder='GtToken from the web capture payload, refer to the documentation tutorial', value=config.get("sparkdesk", "GtToken"))
                    input_sparkdesk_GtToken.style("width:300px")
                with ui.row():
                    input_sparkdesk_app_id = ui.input(label='App ID', placeholder='APPID provided in the cloud platform after applying for the official API', value=config.get("sparkdesk", "app_id"))
                    input_sparkdesk_app_id.style("width:300px")
                    input_sparkdesk_api_secret = ui.input(label='API Secret', placeholder='APISecret provided in the cloud platform after applying for the official API', value=config.get("sparkdesk", "api_secret"))
                    input_sparkdesk_api_secret.style("width:300px")
                    input_sparkdesk_api_key = ui.input(label='API Key', placeholder='APIKey provided in the cloud platform after applying for the official API', value=config.get("sparkdesk", "api_key"))
                    input_sparkdesk_api_key.style("width:300px")
                    lines = ["3.1", "2.1", "1.1"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_sparkdesk_version = ui.select(
                        label='版本', 
                        options=data_json, 
                        value=str(config.get("sparkdesk", "version"))
                    ).style("width:100px")
                with ui.card().style(card_css):
                    ui.label("Langchain_ChatGLM")
                    with ui.row():
                        input_langchain_chatglm_api_ip_port = ui.input(label='API Address', placeholder='Service link after running the API version of langchain_chatglm (requires complete URL)', value=config.get("langchain_chatglm", "api_ip_port"))
                        input_langchain_chatglm_api_ip_port.style("width:400px")
                        lines = ["Model", "Knowledge Base", "Bing"]
                        data_json = {}
                        for line in lines:
                            data_json[line] = line
                        select_langchain_chatglm_chat_type = ui.select(
                            label='类型', 
                            options=data_json, 
                            value=config.get("langchain_chatglm", "chat_type")
                        )
                    with ui.row():
                        input_langchain_chatglm_knowledge_base_id = ui.input(label='Knowledge Base Name', placeholder='Name of the locally available knowledge base, the log also outputs the list of knowledge bases, you can check', value=config.get("langchain_chatglm", "knowledge_base_id"))
                        input_langchain_chatglm_knowledge_base_id.style("width:400px")
                        switch_langchain_chatglm_history_enable = ui.switch('Context Memory', value=config.get("langchain_chatglm", "history_enable")).style(switch_internal_css)
                        input_langchain_chatglm_history_max_len = ui.input(label='Max Memory Length', placeholder='Maximum number of characters for context memory, not recommended to set too large, may cause GPU memory explosion, configure according to the situation', value=config.get("langchain_chatglm", "history_max_len"))
                        input_langchain_chatglm_history_max_len.style("width:400px")
                with ui.card().style(card_css):
                    ui.label("Langchain_ChatChat")
                    with ui.row():
                        input_langchain_chatchat_api_ip_port = ui.input(label='API Address', placeholder='Service link after running the API version of langchain_chatchat (requires complete URL)', value=config.get("langchain_chatchat", "api_ip_port"))
                        input_langchain_chatchat_api_ip_port.style("width:400px")
                        lines = ["Model", "Knowledge Base", "Search Engine"]
                        data_json = {}
                        for line in lines:
                            data_json[line] = line
                        select_langchain_chatchat_chat_type = ui.select(
                            label='类型', 
                            options=data_json, 
                            value=config.get("langchain_chatchat", "chat_type")
                        )
                        switch_langchain_chatchat_history_enable = ui.switch('Context Memory', value=config.get("langchain_chatchat", "history_enable")).style(switch_internal_css)
                        input_langchain_chatchat_history_max_len = ui.input(label='Max Memory Length', placeholder='Maximum number of characters for context memory, not recommended to set too large, may cause GPU memory explosion, configure according to the situation', value=config.get("langchain_chatchat", "history_max_len"))
                        input_langchain_chatchat_history_max_len.style("width:400px")
                    with ui.row():
                        with ui.card().style(card_css):
                            ui.label("Model")
                            with ui.row():
                                input_langchain_chatchat_llm_model_name = ui.input(label='LLM Model', value=config.get("langchain_chatchat", "llm", "model_name"), placeholder='Locally loaded LLM model name')
                                input_langchain_chatchat_llm_temperature = ui.input(label='Temperature', value=config.get("langchain_chatchat", "llm", "temperature"), placeholder='Sampling temperature, controls the randomness of the output, must be a positive number\nThe range is (0.0,1.0], cannot be equal to 0, default value is 0.95\nA larger value will make the output more random and creative; a smaller value will make the output more stable or deterministic\nIt is recommended to adjust the top_p or temperature parameter according to the application scenario, but do not adjust both parameters at the same time')
                                input_langchain_chatchat_llm_max_tokens = ui.input(label='Max Tokens', value=config.get("langchain_chatchat", "llm", "max_tokens"), placeholder='Positive integer greater than 0, not recommended to be too large, you may run out of GPU memory')
                                input_langchain_chatchat_llm_prompt_name = ui.input(label='Prompt Template', value=config.get("langchain_chatchat", "llm", "prompt_name"), placeholder='Locally available prompt word template file name')
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label("Knowledge Base")
                        with ui.row():
                            input_langchain_chatchat_knowledge_base_knowledge_base_name = ui.input(label='Knowledge Base Name', value=config.get("langchain_chatchat", "knowledge_base", "knowledge_base_name"), placeholder='Name of the locally added knowledge base, will automatically retrieve the list of knowledge bases at runtime, output to cmd, please check')
                            input_langchain_chatchat_knowledge_base_top_k = ui.input(label='Matched Search Results', value=config.get("langchain_chatchat", "knowledge_base", "top_k"), placeholder='Number of matched search results')
                            input_langchain_chatchat_knowledge_base_score_threshold = ui.input(label='Knowledge Matching Score Threshold', value=config.get("langchain_chatchat", "knowledge_base", "score_threshold"), placeholder='Between 0.00-2.00')
                            input_langchain_chatchat_knowledge_base_model_name = ui.input(label='LLM Model', value=config.get("langchain_chatchat", "knowledge_base", "model_name"), placeholder='Locally loaded LLM model name')
                            input_langchain_chatchat_knowledge_base_temperature = ui.input(label='Temperature', value=config.get("langchain_chatchat", "knowledge_base", "temperature"), placeholder='Sampling temperature, controls the randomness of the output, must be a positive number\nThe range is (0.0,1.0], cannot be equal to 0, default value is 0.95\nA larger value will make the output more random and creative; a smaller value will make the output more stable or deterministic\nIt is recommended to adjust the top_p or temperature parameter according to the application scenario, but do not adjust both parameters at the same time')
                            input_langchain_chatchat_knowledge_base_max_tokens = ui.input(label='Max Tokens', value=config.get("langchain_chatchat", "knowledge_base", "max_tokens"), placeholder='Positive integer greater than 0, not recommended to be too large, you may run out of GPU memory')
                            input_langchain_chatchat_knowledge_base_prompt_name = ui.input(label='Prompt Template', value=config.get("langchain_chatchat", "knowledge_base", "prompt_name"), placeholder='Locally available prompt word template file name')
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label("Search Engine")
                        with ui.row():
                            lines = ['Bing', 'DuckDuckGo', 'Metaphor']
                            data_json = {}
                            for line in lines:
                                data_json[line] = line
                            select_langchain_chatchat_search_engine_search_engine_name = ui.select(
                                label='搜索引擎', 
                                options=data_json, 
                                value=config.get("langchain_chatchat", "search_engine", "search_engine_name")
                            )
                            input_langchain_chatchat_search_engine_top_k = ui.input(label='Matched Search Results', value=config.get("langchain_chatchat", "search_engine", "top_k"), placeholder='Number of matched search results')
                            input_langchain_chatchat_search_engine_model_name = ui.input(label='LLM Model', value=config.get("langchain_chatchat", "search_engine", "model_name"), placeholder='Locally loaded LLM model name')
                            input_langchain_chatchat_search_engine_temperature = ui.input(label='Temperature', value=config.get("langchain_chatchat", "search_engine", "temperature"), placeholder='Sampling temperature, controls the randomness of the output, must be a positive number\nThe range is (0.0,1.0], cannot be equal to 0, default value is 0.95\nA larger value will make the output more random and creative; a smaller value will make the output more stable or deterministic\nIt is recommended to adjust the top_p or temperature parameter according to the application scenario, but do not adjust both parameters at the same time')
                            input_langchain_chatchat_search_engine_max_tokens = ui.input(label='Max Tokens', value=config.get("langchain_chatchat", "search_engine", "max_tokens"), placeholder='Positive integer greater than 0, not recommended to be too large, you may run out of GPU memory')
                            input_langchain_chatchat_search_engine_prompt_name = ui.input(label='Prompt Template', value=config.get("langchain_chatchat", "search_engine", "prompt_name"), placeholder='Locally available prompt word template file name')
                            
            with ui.card().style(card_css):
                ui.label("Zhipu AI")
                with ui.row():
                    input_zhipu_api_key = ui.input(label='API Key', placeholder='Refer to the official documentation for details. Application link: https://open.bigmodel.cn/usercenter/apikeys', value=config.get("zhipu", "api_key"))
                    input_zhipu_api_key.style("width:400px")
                    lines = ['chatglm_turbo', 'characterglm', 'chatglm_pro', 'chatglm_std', 'chatglm_lite', 'chatglm_lite_32k']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_zhipu_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("zhipu", "model")
                    )
                with ui.row():
                    input_zhipu_top_p = ui.input(label='top_p', placeholder='Another method for temperature sampling, called nucleus sampling\nValue range: (0.0,1.0); open interval, cannot be equal to 0 or 1, default value is 0.7\nThe model considers tokens with top_p probability mass as the result. So, 0.1 means the model decoder only considers tokens from the top 10% probability candidate set\nIt is recommended to adjust either top_p or temperature parameters based on the application scenario, but not both simultaneously', value=config.get("zhipu", "top_p"))
                    input_zhipu_top_p.style("width:200px")
                    input_zhipu_temperature = ui.input(label='temperature', placeholder='Sampling temperature, controls the randomness of the output, must be a positive number\nValue range: (0.0,1.0]; cannot be equal to 0, default value is 0.95\nA larger value will make the output more random and creative; a smaller value will make the output more stable or deterministic\nIt is recommended to adjust either top_p or temperature parameters based on the application scenario, but not both simultaneously', value=config.get("zhipu", "temperature"))
                    input_zhipu_temperature.style("width:200px")
                    switch_zhipu_history_enable = ui.switch('Context Memory', value=config.get("zhipu", "history_enable")).style(switch_internal_css)
                    input_zhipu_history_max_len = ui.input(label='Max Memory Length', placeholder='The maximum length of the remembered question and answer string. Excessively long lengths will discard the earliest memories, use with caution! Configuring too large may result in loss of information', value=config.get("zhipu", "history_max_len"))
                    input_zhipu_history_max_len.style("width:200px")

                with ui.row():
                    input_zhipu_user_info = ui.input(label='User Information', placeholder='User information, required when using characterglm', value=config.get("zhipu", "user_info"))
                    input_zhipu_user_info.style("width:400px")
                    input_zhipu_bot_info = ui.input(label='Role Information', placeholder='Role information, required when using characterglm', value=config.get("zhipu", "bot_info"))
                    input_zhipu_bot_info.style("width:400px")
                    input_zhipu_bot_name = ui.input(label='Role Name', placeholder='Role name, required when using characterglm', value=config.get("zhipu", "bot_name"))
                    input_zhipu_bot_name.style("width:200px")
                    input_zhipu_user_name = ui.input(label='User Name', placeholder='User name, default is "User", required when using characterglm', value=config.get("zhipu", "user_name"))
                    input_zhipu_user_name.style("width:200px")

                with ui.row():
                    switch_zhipu_remove_useless = ui.switch('Remove useless characters', value=config.get("zhipu", "remove_useless")).style(switch_internal_css)
            with ui.card().style(card_css):
                ui.label("Bard")
                with ui.grid(columns=2):
                    input_bard_token = ui.input(label='token', placeholder='Log in to bard, open F12, and obtain the value corresponding to __Secure-1PSID in the cookie.', value=config.get("bard", "token"))
                    input_bard_token.style("width:400px")
            with ui.card().style(card_css):
                ui.label("Wenxinyiyan")
                with ui.row():
                    lines = ['api', 'web']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_yiyan_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("yiyan", "type")
                    ).style("width:100px")
                    switch_yiyan_history_enable = ui.switch('Context Memory', value=config.get("yiyan", "history_enable")).style(switch_internal_css)
                    input_yiyan_history_max_len = ui.input(label='Max Memory Length', value=config.get("yiyan", "history_max_len"), placeholder='The maximum length of the remembered question and answer string. Excessively long lengths will discard the earliest memories, use with caution! Configuring too large may result in loss of information')

                with ui.row():
                    input_yiyan_api_api_key = ui.input(label='API Key', placeholder='Qianfan Big Model application API Key', value=config.get("yiyan", "api", "api_key"))
                    input_yiyan_api_secret_key = ui.input(label='Secret Key', placeholder='Qianfan Big Model application Secret Key', value=config.get("yiyan", "api", "secret_key"))

                with ui.row():
                    input_yiyan_web_api_ip_port = ui.input(label='API Address', placeholder='IP and port address that yiyan-api listens to after startup', value=config.get("yiyan", "web", "api_ip_port"))
                    input_yiyan_web_api_ip_port.style("width:300px")
                    input_yiyan_web_cookie = ui.input(label='Cookie', placeholder='After logging into Wenxinyiyan, skip debugging and capture the cookie from the request packet', value=config.get("yiyan", "web", "cookie"))
                    input_yiyan_web_cookie.style("width:300px")
            with ui.card().style(card_css):
                ui.label("Tongyixingchen")
                with ui.row():
                    input_tongyixingchen_access_token = ui.input(label='API Key', value=config.get("tongyixingchen", "access_token"), placeholder='Apply for an API Key on the official website, then request official access permissions')
                    lines = ['Fixed Character']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tongyixingchen_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("tongyixingchen", "type")
                    ).style("width:100px")
                    switch_tongyixingchen_history_enable = ui.switch('Context Memory', value=config.get("tongyixingchen", "history_enable")).style(switch_internal_css)
                    input_tongyixingchen_history_max_len = ui.input(label='Max Memory Length', value=config.get("tongyixingchen", "history_max_len"), placeholder='The maximum length of the remembered question and answer string. Excessively long lengths will discard the earliest memories, use with caution! Configuring too large may result in loss of information')
                with ui.card().style(card_css):
                    ui.label("Fixed Character")
                    with ui.row():
                        input_tongyixingchen_GDJS_character_id = ui.input(label='Character ID', value=config.get("tongyixingchen", "Fixed Character", "character_id"), placeholder='Created character on the official chat page, then click on the character\'s information to see the ID')
                        input_tongyixingchen_GDJS_top_p = ui.input(label='top_p', value=config.get("tongyixingchen", "Fixed Character", "top_p"), placeholder='For topP generation, the probability threshold of the nucleus sampling method. For example, when set to 0.8, only tokens with a cumulative probability greater than or equal to 0.8 are retained as candidates for random sampling. The value range is (0, 1.0), the larger the value, the higher the randomness of the generation; the smaller the value, the lower the randomness. Default value is 0.95. Note: Do not set the value greater than or equal to 1')
                        input_tongyixingchen_GDJS_temperature = ui.input(label='temperature', value=config.get("tongyixingchen", "Fixed Character", "temperature"), placeholder='A higher value will make the output more random, while a lower value will make the output more focused and determined. Optional, default value is 0.92')
                        input_tongyixingchen_GDJS_seed = ui.input(label='seed', value=config.get("tongyixingchen", "Fixed Character", "seed"), placeholder='Seed for random number generation during model generation, used to control the randomness of model generation. If the same seed is used, the results generated each time will be the same; when you need to reproduce the model generation results, you can use the same seed. The seed parameter supports unsigned 64-bit integer types. Default value is 1683806810')
                    with ui.row():
                        input_tongyixingchen_GDJS_user_id = ui.input(label='User ID', value=config.get("tongyixingchen", "Fixed Character", "user_id"), placeholder='Unique identifier for business system users. The same user cannot engage in parallel conversations and must wait for the end of the previous conversation reply before initiating the next round of conversation')
                        input_tongyixingchen_GDJS_user_name = ui.input(label='Dialogue User Name', value=config.get("tongyixingchen", "Fixed Character", "user_name"), placeholder='Name of the user in the conversation, i.e., your name')
                        input_tongyixingchen_GDJS_role_name = ui.input(label='Fixed Character Name', value=config.get("tongyixingchen", "Fixed Character", "role_name"), placeholder='Role name corresponding to the Role ID, don\'t tell me you don\'t know, you wrote it yourself!')

            with ui.card().style(card_css):
                ui.label("LLM Bot")
                with ui.row():
                    input_my_wenxinworkshop_api_key = ui.input(label='API Key', value=config.get("my_wenxinworkshop", "api_key"), placeholder='For Qianfan Big Model Platform, open the corresponding service. Access the application - create an application, and fill in the API key')
                    input_my_wenxinworkshop_secret_key = ui.input(label='Secret Key', value=config.get("my_wenxinworkshop", "secret_key"), placeholder='For Qianfan Big Model Platform, open the corresponding service. Access the application - create an application, and fill in the secret key')
                    lines = [
                        "ERNIEBot",
                        "ERNIEBot_turbo",
                        "ERNIEBot_4_0",
                        "BLOOMZ_7B",
                        "LLAMA_2_7B",
                        "LLAMA_2_13B",
                        "LLAMA_2_70B",
                        "ERNIEBot_4_0",
                        "QIANFAN_BLOOMZ_7B_COMPRESSED",
                        "QIANFAN_CHINESE_LLAMA_2_7B",
                        "CHATGLM2_6B_32K",
                        "AQUILACHAT_7B",
                        "ERNIE_BOT_8K",
                        "CODELLAMA_7B_INSTRUCT",
                        "XUANYUAN_70B_CHAT",
                        "CHATLAW",
                        "QIANFAN_BLOOMZ_7B_COMPRESSED",
                    ]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_my_wenxinworkshop_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("my_wenxinworkshop", "model")
                    ).style("width:150px")
                    switch_my_wenxinworkshop_history_enable = ui.switch('Context Memory', value=config.get("my_wenxinworkshop", "history_enable")).style(switch_internal_css)
                    input_my_wenxinworkshop_history_max_len = ui.input(label='Max Memory Length', value=config.get("my_wenxinworkshop", "history_max_len"), placeholder='The maximum length of the remembered question and answer string. Excessively long lengths will discard the earliest memories, use with caution! Configuring too large may result in loss of information')
                with ui.row():
                    input_my_wenxinworkshop_temperature = ui.input(label='Temperature', value=config.get("my_wenxinworkshop", "temperature"), placeholder='(0, 1.0] Control the randomness of generated text. Higher temperature values will make the generated text more random and diverse, while lower values will make the generated text more deterministic and consistent.').style("width:200px;")
                    input_my_wenxinworkshop_top_p = ui.input(label='Top-p Selection', value=config.get("my_wenxinworkshop", "top_p"), placeholder='[0, 1.0] Nucleus sampling. This parameter controls the model sampling from tokens with cumulative probability greater than a certain threshold. Higher values produce more diversity, and lower values produce fewer but more certain answers.').style("width:200px;")
                    input_my_wenxinworkshop_penalty_score = ui.input(label='Penalty Score', value=config.get("my_wenxinworkshop", "penalty_score"), placeholder='[1.0, 2.0] Penalty applied to certain words or patterns when generating text. This is a mechanism to adjust the generated content to reduce or avoid unwanted content.').style("width:200px;")
                        
            with ui.card().style(card_css):
                ui.label("Gemini")
                with ui.row():
                    input_gemini_api_key = ui.input(label='API Key', value=config.get("gemini", "api_key"), placeholder='Create API key on Google AI Studio')
                    lines = ["gemini-pro",]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_gemini_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("gemini", "model")
                    ).style("width:150px")
                    switch_gemini_history_enable = ui.switch('Context Memory', value=config.get("gemini", "history_enable")).style(switch_internal_css)
                    input_gemini_history_max_len = ui.input(label='Max Memory Length', value=config.get("gemini", "history_max_len"), placeholder='The maximum length of the remembered question and answer string. Excessively long lengths will discard the earliest memories, use with caution! Configuring too large may result in loss of information')
                    with ui.row():
                        input_gemini_http_proxy = ui.input(label='HTTP Proxy Address', value=config.get("gemini", "http_proxy"), placeholder='HTTP proxy address, requires magic to use, so configuration is needed.').style("width:200px;")
                        input_gemini_https_proxy = ui.input(label='HTTPS Proxy Address', value=config.get("gemini", "https_proxy"), placeholder='HTTPS proxy address, requires magic to use, so configuration is needed.').style("width:200px;")
                    with ui.row():
                        input_gemini_max_output_tokens = ui.input(label='Max Output Tokens', value=config.get("gemini", "max_output_tokens"), placeholder='The maximum number of tokens included in candidate outputs')
                        input_gemini_max_temperature = ui.input(label='Temperature', value=config.get("gemini", "temperature"), placeholder='Control the randomness of the output. Value range is [0.0, 1.0], including 0.0 and 1.0. Higher values make the generated response more diverse and creative, while lower values often lead to more direct responses from the model.')
                        input_gemini_top_p = ui.input(label='Top-p', value=config.get("gemini", "top_p"), placeholder='Maximum cumulative probability of tokens considered during sampling. Sort tokens based on their assigned probabilities to only consider the most likely tokens. Top-k sampling directly limits the maximum number of tokens to consider, while Nucleus sampling limits the number of tokens based on cumulative probability.')
                        input_gemini_top_k = ui.input(label='Top-k', value=config.get("gemini", "top_k"), placeholder='Maximum number of tokens considered during sampling. Top-k sampling considers a set of the top_k most likely tokens. Default value is 40.')

            with ui.card().style(card_css):
                ui.label("Tongyi Qianwen")
                with ui.row():
                    lines = ['web']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tongyi_type = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("tongyi", "type")
                    )
                    input_tongyi_cookie_path = ui.input(label='Cookie Path', placeholder='After logging into Tongyi Qianwen, use the browser plugin Cookie Editor to obtain the Cookie JSON string. Then save the data in a file at this path.', value=config.get("tongyi", "cookie_path"))
                    input_tongyi_cookie_path.style("width:400px")

        with ui.tab_panel(tts_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("Edge-TTS")
                with ui.row():
                    with open('data/edge-tts-voice-list.txt', 'r') as file:
                        file_content = file.read()
                    # Split content by lines and remove newlines at the end of each line
                    lines = file_content.strip().split('\n')
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_edge_tts_voice = ui.select(
                        label='说话人', 
                        options=data_json, 
                        value=config.get("edge-tts", "voice")
                    )
                    input_edge_tts_rate = ui.input(
                        label='Speed Gain', 
                        placeholder='Speed gain, default is +0%, can be increased or decreased. Be careful with the + - % format, as it may affect speech synthesis.',
                        value=config.get("edge-tts", "rate")
                    ).style("width:200px;")

                    input_edge_tts_volume = ui.input(
                        label='Volume Gain', 
                        placeholder='Volume gain, default is +0%, can be increased or decreased. Be careful with the + - % format, as it may affect speech synthesis.',
                        value=config.get("edge-tts", "volume")
                    ).style("width:200px;")

            with ui.card().style(card_css):
                ui.label("VITS")
                with ui.row():
                        select_vits_type = ui.select(
                            label='Type',
                            options={'vits': 'vits', 'bert_vits2': 'bert_vits2'},
                            value=config.get("vits", "type")
                        ).style("width:200px;")
                        input_vits_config_path = ui.input(
                            label='Configuration File Path',
                            placeholder='Model configuration file storage path',
                            value=config.get("vits", "config_path")
                        ).style("width:200px;")

                        input_vits_api_ip_port = ui.input(
                            label='API Address',
                            placeholder='vits-simple-api listening IP and port address',
                            value=config.get("vits", "api_ip_port")
                        ).style("width:300px;")

                with ui.row():
                        input_vits_id = ui.input(
                            label='Speaker ID',
                            placeholder='API assigns IDs to the configuration file, usually in Pinyin order starting from 0',
                            value=config.get("vits", "id")
                        ).style("width:200px;")

                        select_vits_lang = ui.select(
                            label='Language',
                            options={'Auto': 'Auto', 'Chinese': 'Chinese', 'English': 'English', 'Japanese': 'Japanese'},
                            value=config.get("vits", "lang")
                        )
                        input_vits_length = ui.input(
                            label='Speech Length',
                            placeholder='Adjust speech length, equivalent to adjusting speech speed (larger values result in slower speed)',
                            value=config.get("vits", "length")
                        ).style("width:200px;")

                with ui.row():
                        input_vits_noise = ui.input(
                            label='Noise',
                            placeholder='Control the degree of emotional changes',
                            value=config.get("vits", "noise")
                        ).style("width:200px;")

                        input_vits_noisew = ui.input(
                            label='Noise Deviation',
                            placeholder='Control the length of phoneme pronunciation',
                            value=config.get("vits", "noisew")
                        ).style("width:200px;")

                        input_vits_max = ui.input(
                            label='Segmentation Threshold',
                            placeholder='Segments text based on punctuation. A segment is formed when the sum exceeds max. max<=0 means no segmentation.',
                            value=config.get("vits", "max")
                        ).style("width:200px;")

                        input_vits_format = ui.input(
                            label='Audio Format',
                            placeholder='Supports wav, ogg, silk, mp3, flac',
                            value=config.get("vits", "format")
                        ).style("width:200px;")

                        input_vits_sdp_radio = ui.input(
                            label='SDP/DP Mix Ratio',
                            placeholder='SDP/DP mix ratio: the ratio of SDP during synthesis. Higher ratio theoretically leads to greater intonation variance in synthesized speech.',
                            value=config.get("vits", "sdp_radio")
                        ).style("width:200px;")

            with ui.card().style(card_css):
                ui.label("bert_vits2")
                with ui.row():
                        select_bert_vits2_type = ui.select(
                            label='Type',
                            options={'hiyori': 'hiyori'},
                            value=config.get("bert_vits2", "type")
                        ).style("width:200px;")
                        input_bert_vits2_api_ip_port = ui.input(
                            label='API Address',
                            placeholder='bert_vits2 listening IP and port address after Hiyori UI startup',
                            value=config.get("bert_vits2", "api_ip_port")
                        ).style("width:300px;")

                with ui.row():
                        input_vits_model_id = ui.input(
                            label='Model ID',
                            placeholder='Assigning IDs to the configuration file, usually in Pinyin order starting from 0',
                            value=config.get("bert_vits2", "model_id")
                        ).style("width:200px;")
                        input_vits_speaker_name = ui.input(
                            label='Speaker Name',
                            value=config.get("bert_vits2", "speaker_name"),
                            placeholder='Name corresponding to the speaker in the configuration file'
                        ).style("width:200px;")
                        input_vits_speaker_id = ui.input(
                            label='Speaker ID',
                            value=config.get("bert_vits2", "speaker_id"),
                            placeholder='Assigning IDs to the configuration file, usually in Pinyin order starting from 0'
                        ).style("width:200px;")

                        select_bert_vits2_language = ui.select(
                            label='Language',
                            options={'auto': 'auto', 'ZH': 'ZH', 'JP': 'JP', 'EN': 'EN'},
                            value=config.get("bert_vits2", "language")
                        ).style("width:50px;")
                        input_bert_vits2_length = ui.input(
                            label='Speech Length',
                            placeholder='Adjust speech length, equivalent to adjusting speech speed (larger values result in slower speed)',
                            value=config.get("bert_vits2", "length")
                        ).style("width:200px;")

                with ui.row():
                        input_bert_vits2_noise = ui.input(
                            label='Noise',
                            value=config.get("bert_vits2", "noise"),
                            placeholder='Control the degree of emotional changes'
                        ).style("width:200px;")
                        input_bert_vits2_noisew = ui.input(
                            label='Noise Deviation',
                            value=config.get("bert_vits2", "noisew"),
                            placeholder='Control the length of phoneme pronunciation'
                        ).style("width:200px;")
                        input_bert_vits2_sdp_radio = ui.input(
                            label='SDP/DP Mix Ratio',
                            value=config.get("bert_vits2", "sdp_radio"),
                            placeholder='SDP/DP mix ratio: the ratio of SDP during synthesis. Higher ratio theoretically leads to greater intonation variance in synthesized speech.'
                        ).style("width:200px;")

                with ui.row():
                        input_bert_vits2_emotion = ui.input(
                            label='Emotion',
                            value=config.get("bert_vits2", "emotion"),
                            placeholder='Emotion'
                        ).style("width:200px;")
                        input_bert_vits2_style_text = ui.input(
                            label='Style Text',
                            value=config.get("bert_vits2", "style_text"),
                            placeholder='Style text'
                        ).style("width:200px;")
                        input_bert_vits2_style_weight = ui.input(
                            label='Style Weight',
                            value=config.get("bert_vits2", "style_weight"),
                            placeholder='Ratio of BERT mixing between main text and auxiliary text. 0 means only main text, 1 means only auxiliary text (0.7)'
                        ).style("width:200px;")
                        switch_bert_vits2_auto_translate = ui.switch(
                            'Auto Translate',
                            value=config.get("bert_vits2", "auto_translate")
                        ).style(switch_internal_css)
                        switch_bert_vits2_auto_split = ui.switch(
                            'Auto Split',
                            value=config.get("bert_vits2", "auto_split")
                        ).style(switch_internal_css)

            with ui.card().style(card_css):
                ui.label("VITS-Fast")
                with ui.row():
                        input_vits_fast_config_path = ui.input(
                            label='Configuration File Path',
                            placeholder='Path to the configuration file, for example: E:\\inference\\finetune_speaker.json',
                            value=config.get("vits_fast", "config_path")
                        )
                        input_vits_fast_api_ip_port = ui.input(
                            label='API Address',
                            placeholder='Link to the inference service (requires a complete URL)',
                            value=config.get("vits_fast", "api_ip_port")
                        )
                        input_vits_fast_character = ui.input(
                            label='Speaker',
                            placeholder='Selected speaker, one of the speakers in the configuration file',
                            value=config.get("vits_fast", "character")
                        )
                        select_vits_fast_language = ui.select(
                            label='Language',
                            options={'Auto Detect': 'Auto Detect', 'Japanese': 'Japanese', 'Simplified Chinese': 'Simplified Chinese', 'English': 'English', 'Mix': 'Mix'},
                            value=config.get("vits_fast", "language")
                        )
                        input_vits_fast_speed = ui.input(
                            label='Speech Speed',
                            placeholder='Speech speed, default is 1',
                            value=config.get("vits_fast", "speed")
                        )

                with ui.card().style(card_css):
                        ui.label("elevenlabs")
                        with ui.row():
                            input_elevenlabs_api_key = ui.input(
                                label='API Key',
                                placeholder='elevenlabs API key, can be left blank. Default has a certain amount of free usage.',
                                value=config.get("elevenlabs", "api_key")
                            )
                            input_elevenlabs_voice = ui.input(
                                label='Speaker',
                                placeholder='Selected speaker name',
                                value=config.get("elevenlabs", "voice")
                            )
                            input_elevenlabs_model = ui.input(
                                label='Model',
                                placeholder='Selected model',
                                value=config.get("elevenlabs", "model")
                            )

            with ui.card().style(card_css):
                ui.label("genshinvoice.top")
                with ui.row():
                    with open('data/genshinvoice_top_speak_list.txt', 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    # Split the content into lines and remove the newline character at the end of each line
                    lines = file_content.strip().split('\n')
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tts_ai_lab_top_speaker = ui.select(
                        label='角色', 
                        options=data_json, 
                        value=config.get("tts_ai_lab_top", "speaker")
                    )

                    input_genshinvoice_top_noise = ui.input(
                        label='Emotion',
                        placeholder='Control the degree of emotion change, default is 0.2',
                        value=config.get("genshinvoice_top", "noise")
                    )
                    input_genshinvoice_top_noisew = ui.input(
                        label='Phoneme Length',
                        placeholder='Control the degree of phoneme length change, default is 0.9',
                        value=config.get("genshinvoice_top", "noisew")
                    )
                    input_genshinvoice_top_length = ui.input(
                        label='Speech Speed',
                        placeholder='Can be used to control the overall speech speed, default is 1.2',
                        value=config.get("genshinvoice_top", "length")
                    )
                    input_genshinvoice_top_format = ui.input(
                        label='Format',
                        placeholder='The original interface synthesizes speech in WAV format. In the case of synthesizing speech in MP3 format, there will be a slowdown due to audio format conversion. It is recommended to choose WAV format.',
                        value=config.get("genshinvoice_top", "format")
                    )
                    select_genshinvoice_top_language = ui.select(
                        label='Language', 
                        options={'Chinese': 'ZH', 'English': 'EN', 'Japanese': 'JP'}, 
                        value=config.get("genshinvoice_top", "language")
                    ).style("width:100px")

            with ui.card().style(card_css):
                ui.label("tts.ai-lab.top")
                with ui.row():
                    with open('data/tts_ai_lab_top_speak_list.txt', 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    # Split the content into lines and remove the newline character at the end of each line
                    lines = file_content.strip().split('\n')
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tts_ai_lab_top_speaker = ui.select(
                        label='Character', 
                        options=data_json, 
                        value=config.get("tts_ai_lab_top", "speaker")
                    )
                    input_tts_ai_lab_top_appid = ui.input(
                        label='appid',
                        placeholder='Go to https://tts.ai-hobbyist.org/, use F12 to capture the synthesis request package, and get it from the payload',
                        value=config.get("tts_ai_lab_top", "appid")
                    )
                    input_tts_ai_lab_top_token = ui.input(
                        label='token',
                        placeholder='Go to https://tts.ai-hobbyist.org/, use F12 to capture the synthesis request package, and get it from the payload',
                        value=config.get("tts_ai_lab_top", "token")
                    )
                    input_tts_ai_lab_top_noise = ui.input(
                        label='Emotion',
                        placeholder='Control the degree of emotion change, default is 0.2',
                        value=config.get("tts_ai_lab_top", "noise")
                    )
                    input_tts_ai_lab_top_noisew = ui.input(
                        label='Phoneme Length',
                        placeholder='Control the degree of phoneme length change, default is 0.9',
                        value=config.get("tts_ai_lab_top", "noisew")
                    )
                    input_tts_ai_lab_top_length = ui.input(
                        label='Speech Speed',
                        placeholder='Can be used to control the overall speech speed, default is 1.2',
                        value=config.get("tts_ai_lab_top", "length")
                    )
                    input_tts_ai_lab_top_sdp_ratio = ui.input(
                        label='SDP/DP Ratio',
                        placeholder='SDP/DP Ratio: The ratio of SDP during synthesis. Theoretically, the higher this ratio, the greater the pitch variance of the synthesized speech.',
                        value=config.get("tts_ai_lab_top", "sdp_ratio")
                    )

            with ui.card().style(card_css):
                ui.label("bark_gui")
                with ui.row():
                    input_bark_gui_api_ip_port = ui.input(
                        label='API Address',
                        placeholder='IP and port address where bark-gui',
                        value=config.get("bark_gui", "api_ip_port")
                    ).style("width:200px;")
                    input_bark_gui_spk = ui.input(
                        label='Speaker',
                        placeholder='Selected speaker, corresponding to the voice in webui',
                        value=config.get("bark_gui", "spk")
                    ).style("width:200px;")

                    input_bark_gui_generation_temperature = ui.input(
                        label='Generation Temperature',
                        placeholder='Control the randomness during synthesis. Higher values (close to 1.0) make the output more random, while lower values (close to 0.0) make it more deterministic and focused.',
                        value=config.get("bark_gui", "generation_temperature")
                    ).style("width:200px;")
                    input_bark_gui_waveform_temperature = ui.input(
                        label='Waveform Temperature',
                        placeholder='Similar to generation_temperature, but specifically controls the randomness of the waveform generated from the speech model',
                        value=config.get("bark_gui", "waveform_temperature")
                    ).style("width:200px;")
                with ui.row():
                    input_bark_gui_end_of_sentence_probability = ui.input(
                        label='End-of-Sentence Probability',
                        placeholder='This parameter determines the likelihood of adding pauses or intervals at the end of a sentence. Higher values increase the chance of pauses, while lower values decrease it.',
                        value=config.get("bark_gui", "end_of_sentence_probability")
                    ).style("width:200px;")
                    switch_bark_gui_quick_generation = ui.switch(
                        'Quick Generation',
                        value=config.get("bark_gui", "quick_generation")
                    ).style(switch_internal_css)
                    input_bark_gui_seed = ui.input(
                        label='Random Seed',
                        placeholder='Seed value for the random number generator. Using a specific seed ensures that the speech output for the same input text is consistent. A value of -1 indicates using a random seed.',
                        value=config.get("bark_gui", "seed")
                    ).style("width:200px;")
                    input_bark_gui_batch_count = ui.input(
                        label='Batch Count',
                        placeholder='Specify the number of sentences or utterances for batch synthesis. Setting it to 1 means synthesizing one sentence at a time.',
                        value=config.get("bark_gui", "batch_count")
                    ).style("width:200px;")

            with ui.card().style(card_css):
                ui.label("vall_e_x")
                with ui.row():
                    input_vall_e_x_api_ip_port = ui.input(
                        label='API Address',
                        placeholder='IP and port address where VALL-E-X is running',
                        value=config.get("vall_e_x", "api_ip_port")
                    ).style("width:200px;")
                    select_vall_e_x_language = ui.select(
                        label='Language',
                        options={'auto-detect': 'auto-detect', 'English': 'English', '中文': '中文', '日本語': '日本語', 'Mix': 'Mix'},
                        value=config.get("vall_e_x", "language")
                    ).style("width:200px;")

                    select_vall_e_x_accent = ui.select(
                        label='Accent',
                        options={'no-accent': 'no-accent', 'English': 'English', '中文': '中文', '日本語': '日本語'},
                        value=config.get("vall_e_x", "accent")
                    ).style("width:200px;")

                    input_vall_e_x_voice_preset = ui.input(
                        label='Voice Preset',
                        placeholder='VALL-E-X speaker preset name (Prompt name)',
                        value=config.get("vall_e_x", "voice_preset")
                    ).style("width:300px;")
                    input_vall_e_x_voice_preset_file_path = ui.input(
                        label='Voice Preset File Path',
                        placeholder='VALL-E-X speaker preset file path (npz)',
                        value=config.get("vall_e_x", "voice_preset_file_path")
                    ).style("width:300px;")

            with ui.card().style(card_css):
                ui.label("OpenAI TTS")
                with ui.row():
                    select_openai_tts_type = ui.select(
                        label='Type',
                        options={'api': 'api', 'huggingface': 'huggingface'},
                        value=config.get("openai_tts", "type")
                    ).style("width:200px;")
                    input_openai_tts_api_ip_port = ui.input(
                        label='API Address',
                        value=config.get("openai_tts", "api_ip_port"),
                        placeholder='API address corresponding to the project on huggingface'
                    ).style("width:200px;")
                with ui.row():
                    select_openai_tts_model = ui.select(
                        label='Model',
                        options={'tts-1': 'tts-1', 'tts-1-hd': 'tts-1-hd'},
                        value=config.get("openai_tts", "model")
                    ).style("width:200px;")
                    select_openai_tts_voice = ui.select(
                        label='Speaker',
                        options={
                            'alloy': 'alloy',
                            'echo': 'echo',
                            'fable': 'fable',
                            'onyx': 'onyx',
                            'nova': 'nova',
                            'shimmer': 'shimmer'
                        },
                        value=config.get("openai_tts", "voice")
                    ).style("width:200px;")
                    input_openai_tts_api_key = ui.input(
                        label='API Key',
                        value=config.get("openai_tts", "api_key"),
                        placeholder='OpenAI API KEY'
                    ).style("width:200px;")

            with ui.card().style(card_css):
                ui.label("Reecho AI")
                with ui.row():
                    input_reecho_ai_Authorization = ui.input(
                        label='API Key',
                        value=config.get("reecho_ai", "Authorization"),
                        placeholder='API Key'
                    ).style("width:200px;")
                    input_reecho_ai_model = ui.input(
                        label='Model ID',
                        value=config.get("reecho_ai", "model"),
                        placeholder='Model ID to use (currently unified as reecho-neural-voice-001)'
                    ).style("width:200px;")
                    input_reecho_ai_voiceId = ui.input(
                        label='Voice ID',
                        value=config.get("reecho_ai", "voiceId"),
                        placeholder='Voice ID to use, must be in the account’s role list library, remember to expand details'
                    ).style("width:300px;")
                with ui.row():
                    number_reecho_ai_randomness = ui.number(
                        label='Randomness',
                        value=config.get("reecho_ai", "randomness"),
                        format='%d',
                        min=0,
                        max=100,
                        step=1,
                        placeholder='Randomness (0-100, default: 97)'
                    ).style("width:200px;")
                    number_reecho_ai_stability_boost = ui.number(
                        label='Stability Boost',
                        value=config.get("reecho_ai", "stability_boost"),
                        format='%d',
                        min=0,
                        max=100,
                        step=1,
                        placeholder='Stability Boost (0-100, default: 40)'
                    ).style("width:200px;")
            with ui.card().style(card_css):
                ui.label("Gradio")
                with ui.row():
                    textarea_gradio_tts_request_parameters = ui.textarea(
                        label='Request Parameters',
                        value=config.get("gradio_tts", "request_parameters"),
                        placeholder='Pay attention to the format! {content} is used to replace the text to be synthesized.\nurl is the request address;\nfn_index is the index corresponding to the API;\ndata_analysis is the data analysis rule, currently only supports index indexing of tuples and lists, please refer to the template for configuration\nKeys do not affect the request. Note that the order of parameters needs to be consistent with the API request\nData can be converted to str using the json library, which is much more reliable for configuration'
                    ).style("width:800px;")

        
        with ui.tab_panel(svc_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("DDSP-SVC")
                with ui.row():
                    switch_ddsp_svc_enable = ui.switch('Enable', value=config.get("ddsp_svc", "enable")).style(switch_internal_css)
                    input_ddsp_svc_config_path = ui.input(
                        label='Configuration File Path',
                        placeholder='Path to the model configuration file config.yaml (optional, not currently used)',
                        value=config.get("ddsp_svc", "config_path")
                    )
                    input_ddsp_svc_config_path.style("width:400px")

                    input_ddsp_svc_api_ip_port = ui.input(
                        label='API Address',
                        placeholder='IP and port where the flask_api service is running, e.g., http://127.0.0.1:6844',
                        value=config.get("ddsp_svc", "api_ip_port")
                    )
                    input_ddsp_svc_api_ip_port.style("width:400px")
                    input_ddsp_svc_fSafePrefixPadLength = ui.input(
                        label='Safe Prefix Padding Length',
                        placeholder='Safe prefix padding length, default is 0',
                        value=config.get("ddsp_svc", "fSafePrefixPadLength")
                    )
                    input_ddsp_svc_fSafePrefixPadLength.style("width:300px")
                with ui.row():
                    input_ddsp_svc_fPitchChange = ui.input(
                        label='Pitch Change',
                        placeholder='Pitch setting, default is 0',
                        value=config.get("ddsp_svc", "fPitchChange")
                    )
                    input_ddsp_svc_fPitchChange.style("width:300px")
                    input_ddsp_svc_sSpeakId = ui.input(
                        label='Speaker ID',
                        placeholder='Speaker ID, needs to correspond with model data, default is 0',
                        value=config.get("ddsp_svc", "sSpeakId")
                    )
                    input_ddsp_svc_sSpeakId.style("width:400px")

                    input_ddsp_svc_sampleRate = ui.input(
                        label='Sample Rate',
                        placeholder='Sample rate required by DAW, default is 44100',
                        value=config.get("ddsp_svc", "sampleRate")
                    )
                    input_ddsp_svc_sampleRate.style("width:300px")
            with ui.card().style(card_css):
                ui.label("SO-VITS-SVC")
                with ui.row():
                    switch_so_vits_svc_enable = ui.switch('Enable', value=config.get("so_vits_svc", "enable")).style(switch_internal_css)
                    input_so_vits_svc_config_path = ui.input(
                        label='Configuration File Path',
                        placeholder='Path to the model configuration file config.json',
                        value=config.get("so_vits_svc", "config_path")
                    )
                    input_so_vits_svc_config_path.style("width:400px")
                with ui.grid(columns=2):
                    input_so_vits_svc_api_ip_port = ui.input(
                        label='API Address',
                        placeholder='IP and port where the flask_api_full_song service is running, e.g., http://127.0.0.1:1145',
                        value=config.get("so_vits_svc", "api_ip_port")
                    )
                    input_so_vits_svc_api_ip_port.style("width:400px")
                    input_so_vits_svc_spk = ui.input(
                        label='Speaker',
                        placeholder='Speaker, needs to correspond with the configuration file content',
                        value=config.get("so_vits_svc", "spk")
                    )
                    input_so_vits_svc_spk.style("width:400px") 
                    input_so_vits_svc_tran = ui.input(
                        label='Pitch',
                        placeholder='Pitch setting, default is 1',
                        value=config.get("so_vits_svc", "tran")
                    )
                    input_so_vits_svc_tran.style("width:300px")
                    input_so_vits_svc_wav_format = ui.input(
                        label='Output Audio Format',
                        placeholder='Output format of the audio after synthesis',
                        value=config.get("so_vits_svc", "wav_format")
                    )
                    input_so_vits_svc_wav_format.style("width:300px")


        with ui.tab_panel(visual_body_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("Live2D")
                with ui.row():
                    switch_live2d_enable = ui.switch('Enable', value=config.get("live2d", "enable")).style(switch_internal_css)
                    input_live2d_port = ui.input(
                        label='Port',
                        value=config.get("live2d", "port"),
                        placeholder='Port number where the web service is running, default: 12345, range: 0-65535 (do not change unless necessary)'
                    )
                    # input_live2d_name = ui.input(
                    #     label='Model Name',
                    #     value=config.get("live2d", "name"),
                    #     placeholder='Model name, models are located in the Live2D\\live2d-model path, ensure the path and model content match'
                    # )

            with ui.card().style(card_css):
                ui.label("xuniren")
                with ui.row():
                    input_xuniren_api_ip_port = ui.input(
                        label='API Address',
                        value=config.get("xuniren", "api_ip_port"),
                        placeholder='IP and port where xuniren application is running API'
                    )

            with ui.card().style(card_css):
                ui.label("Unity")
                with ui.row():
                    # switch_unity_enable = ui.switch('Enable', value=config.get("unity", "enable")).style(switch_internal_css)
                    input_unity_api_ip_port = ui.input(
                        label='API Address',
                        value=config.get("unity", "api_ip_port"),
                        placeholder='IP and port where the HTTP relay station for Unity application is listening'
                    )
                    input_unity_password = ui.input(
                        label='Password',
                        value=config.get("unity", "password"),
                        placeholder='Password for the HTTP relay station used by the Unity application'
                    )
                    
        with ui.tab_panel(copywriting_page).style(tab_panel_css):
            with ui.row():
                switch_copywriting_auto_play = ui.switch('Auto Play', value=config.get("copywriting", "auto_play")).style(switch_internal_css)
                switch_copywriting_random_play = ui.switch('Random Audio Play', value=config.get("copywriting", "random_play")).style(switch_internal_css)
                input_copywriting_audio_interval = ui.input(
                    label='Audio Interval',
                    value=config.get("copywriting", "audio_interval"),
                    placeholder='Interval time between audio playback of copywriting. Time between the completion of the previous copywriting playback and the start of the next one.'
                )
                input_copywriting_switching_interval = ui.input(
                    label='Switching Interval',
                    value=config.get("copywriting", "switching_interval"),
                    placeholder='Interval time for switching between copywriting audio and danmaku audio (and vice versa). When playing copywriting and a danmaku trigger occurs and is synthesized, playback will pause for this interval before playing the danmaku reply audio.'
                )
            with ui.row():
                input_copywriting_index = ui.input(
                    label='Copywriting Index',
                    value="",
                    placeholder='Sort number of the copywriting group. The first group is 1, the second group is 2, and so on. Please enter a positive integer.'
                )
                button_copywriting_add = ui.button('Add Copywriting Group', on_click=copywriting_add, color=button_internal_color).style(button_internal_css)
                button_copywriting_del = ui.button('Delete Copywriting Group', on_click=lambda: copywriting_del(input_copywriting_index.value), color=button_internal_color).style(button_internal_css)

            copywriting_config_var = {}
            copywriting_config_card = ui.card()
            for index, copywriting_config in enumerate(config.get("copywriting", "config")):
                with copywriting_config_card.style(card_css):
                    with ui.row():
                        copywriting_config_var[str(5 * index)] = ui.input(
                            label=f"Copywriting Storage Path #{index + 1}",
                            value=copywriting_config["file_path"],
                            placeholder='Path where copywriting files are stored. Not recommended to change.'
                        ).style("width:200px;")
                        copywriting_config_var[str(5 * index + 1)] = ui.input(
                            label=f"Audio Storage Path #{index + 1}",
                            value=copywriting_config["audio_path"],
                            placeholder='Path where copywriting audio files are stored. Not recommended to change.'
                        ).style("width:200px;")
                        copywriting_config_var[str(5 * index + 2)] = ui.input(
                            label=f"Continuous Playback Count #{index + 1}",
                            value=copywriting_config["continuous_play_num"],
                            placeholder='Number of audio files to play continuously in the copywriting playback list. If exceeded, it will switch to the next copywriting list.'
                        ).style("width:200px;")
                        copywriting_config_var[str(5 * index + 3)] = ui.input(
                            label=f"Continuous Playback Time #{index + 1}",
                            value=copywriting_config["max_play_time"],
                            placeholder='Duration of continuous playback of audio in the copywriting playback list. If exceeded, it will switch to the next copywriting list.'
                        ).style("width:200px;")
                        copywriting_config_var[str(5 * index + 4)] = ui.textarea(
                            label=f"Playback List #{index + 1}",
                            value=textarea_data_change(copywriting_config["play_list"]),
                            placeholder='Enter the full names of audio files to be played here. After filling in, click Save Configuration. Copy the full names of the audio files from the audio list, separated by line breaks. Do not fill in arbitrarily.'
                        ).style("width:500px;")

        with ui.tab_panel(integral_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("Common")
                with ui.grid(columns=3):
                    switch_integral_enable = ui.switch('Enable', value=config.get("integral", "enable")).style(switch_internal_css)
            with ui.card().style(card_css):
                ui.label("Sign-in")
                with ui.grid(columns=3):
                    switch_integral_sign_enable = ui.switch('Enable', value=config.get("integral", "sign", "enable")).style(switch_internal_css)
                    input_integral_sign_get_integral = ui.input(
                        label='Get Integral Points',
                        value=config.get("integral", "sign", "get_integral"),
                        placeholder='Number of integral points obtained after successful sign-in. Please enter a positive integer!'
                    )
                    textarea_integral_sign_cmd = ui.textarea(
                        label='Commands',
                        value=textarea_data_change(config.get("integral", "sign", "cmd")),
                        placeholder='The following commands can trigger the sign-in function when sent in the danmaku. Separate commands with line breaks.'
                    )
                with ui.card().style(card_css):
                    ui.label("Copywriting")
                    integral_sign_copywriting_var = {}
                    for index, integral_sign_copywriting in enumerate(config.get("integral", "sign", "copywriting")):
                        with ui.grid(columns=2):
                            integral_sign_copywriting_var[str(2 * index)] = ui.input(
                                label=f"Sign-in Number Interval #{index}",
                                value=integral_sign_copywriting["sign_num_interval"],
                                placeholder='Trigger the corresponding copywriting within this interval of sign-in numbers. Use a hyphen to delineate the interval, including boundary values.'
                            )
                            integral_sign_copywriting_var[str(2 * index + 1)] = ui.textarea(
                                label=f"Copywriting #{index}",
                                value=textarea_data_change(integral_sign_copywriting["copywriting"]),
                                placeholder='Content of the copywriting triggered within this sign-in interval. Separate with line breaks.'
                            ).style("width:400px;")

            with ui.card().style(card_css):
                ui.label("Gift")
                with ui.grid(columns=3):
                    switch_integral_gift_enable = ui.switch('Enable', value=config.get("integral", "gift", "enable")).style(switch_internal_css)
                    input_integral_gift_get_integral_proportion = ui.input(
                        label='Get Integral Proportion',
                        value=config.get("integral", "gift", "get_integral_proportion"),
                        placeholder='This ratio is linked to the real amount (in yuan) of the gift. Default is 1 yuan = 10 integral points.'
                    )
                with ui.card().style(card_css):
                    ui.label("Copywriting")
                    integral_gift_copywriting_var = {}
                    for index, integral_gift_copywriting in enumerate(config.get("integral", "gift", "copywriting")):
                        with ui.grid(columns=2):
                            integral_gift_copywriting_var[str(2 * index)] = ui.input(
                                label=f"Gift Price Interval #{index}",
                                value=integral_gift_copywriting["gift_price_interval"],
                                placeholder='Trigger the corresponding copywriting within this interval of gift prices. Use a hyphen to delineate the interval, including boundary values.'
                            )
                            integral_gift_copywriting_var[str(2 * index + 1)] = ui.textarea(
                                label=f"Copywriting #{index}",
                                value=textarea_data_change(integral_gift_copywriting["copywriting"]),
                                placeholder='Content of the copywriting triggered within this gift interval. Separate with line breaks.'
                            ).style("width:400px;")

            with ui.card().style(card_css):
                ui.label("Entrance")
                with ui.grid(columns=3):
                    switch_integral_entrance_enable = ui.switch('Enable', value=config.get("integral", "entrance", "enable")).style(switch_internal_css)
                    input_integral_entrance_get_integral = ui.input(
                        label='Get Integral Points',
                        value=config.get("integral", "entrance", "get_integral"),
                        placeholder='Number of integral points obtained after successful entrance. Please enter a positive integer!'
                    )
                with ui.card().style(card_css):
                    ui.label("Copywriting")
                    integral_entrance_copywriting_var = {}
                    for index, integral_entrance_copywriting in enumerate(config.get("integral", "entrance", "copywriting")):
                        with ui.grid(columns=2):
                            integral_entrance_copywriting_var[str(2 * index)] = ui.input(
                                label=f"Entrance Number Interval #{index}",
                                value=integral_entrance_copywriting["entrance_num_interval"],
                                placeholder='Trigger the corresponding copywriting within this interval of entrance numbers. Use a hyphen to delineate the interval, including boundary values.'
                            )
                            integral_entrance_copywriting_var[str(2 * index + 1)] = ui.textarea(
                                label=f"Copywriting #{index}",
                                value=textarea_data_change(integral_entrance_copywriting["copywriting"]),
                                placeholder='Content of the copywriting triggered within this entrance interval. Separate with line breaks.'
                            ).style("width:400px;")

            with ui.card().style(card_css):
                ui.label("CRUD (Create, Read, Update, Delete)")
                with ui.card().style(card_css):
                    ui.label("Query")
                    with ui.grid(columns=3):
                        switch_integral_crud_query_enable = ui.switch('Enable', value=config.get("integral", "crud", "query", "enable")).style(switch_internal_css)
                        textarea_integral_crud_query_cmd = ui.textarea(
                            label="Commands",
                            value=textarea_data_change(config.get("integral", "crud", "query", "cmd")),
                            placeholder='The following commands can trigger the query function when sent in the danmaku. Separate commands with line breaks.'
                        )
                        textarea_integral_crud_query_copywriting = ui.textarea(
                            label="Copywriting",
                            value=textarea_data_change(config.get("integral", "crud", "query", "copywriting")),
                            placeholder='Content returned after triggering the query function. Separate with line breaks.'
                        ).style("width:400px;")

        with ui.tab_panel(talk_page).style(tab_panel_css):   
            with ui.row():
                # Get a list of all audio input devices
                audio_device_info_list = common.get_all_audio_device_info("in")
                # Convert the list into a dictionary with device index as keys and device info as values
                audio_device_info_dict = {str(device['device_index']): device['device_info'] for device in audio_device_info_list}

                logging.debug(f"Audio input devices={audio_device_info_dict}")

                # Create a dropdown select element for choosing the audio input device
                select_talk_device_index = ui.select(
                    label='Audio Input Device',
                    options=audio_device_info_dict,
                    value=config.get("talk", "device_index")
                ).style("width:300px;")

                # Input field for the user's name
                input_talk_username = ui.input(
                    label="Your Name",
                    value=config.get("talk", "username"),
                    placeholder="Your name as shown in the logs, currently has no substantial effect."
                ).style("width:200px;")

                # Switch for enabling continuous talk
                switch_talk_continuous_talk = ui.switch(
                    'Continuous Talk',
                    value=config.get("talk", "continuous_talk")
                ).style(switch_internal_css)

            with ui.row():
                # Dropdown for selecting the recording type
                data_json = {}
                for line in ["google", "baidu", "faster_whisper"]:
                    data_json[line] = line
                select_talk_type = ui.select(
                    label='录音类型', 
                    options=data_json, 
                    value=config.get("talk", "type")
                ).style("width:200px;")

                # Read trigger key options from a file
                with open('data/keyboard.txt', 'r') as file:
                    file_content = file.read()
                # Split the content into lines and create options for the trigger key dropdowns
                lines = file_content.strip().split('\n')
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_talk_trigger_key = ui.select(
                    label='录音按键', 
                    options=data_json, 
                    value=config.get("talk", "trigger_key")
                ).style("width:100px;")
                select_talk_stop_trigger_key = ui.select(
                    label='停录按键', 
                    options=data_json, 
                    value=config.get("talk", "stop_trigger_key")
                ).style("width:100px;")

                # Input fields for volume and silence thresholds
                input_talk_volume_threshold = ui.input(
                    label='Volume Threshold',
                    value=config.get("talk", "volume_threshold"),
                    placeholder='Volume threshold, the starting volume value to trigger recording.'
                )
                input_talk_silence_threshold = ui.input(
                    label='Silence Threshold',
                    value=config.get("talk", "silence_threshold"),
                    placeholder='Silence threshold, the minimum volume value to trigger stop recording.'
                )
                # Input fields for recording parameters (CHANNELS and RATE)
                input_talk_silence_CHANNELS = ui.input(
                    label='CHANNELS',
                    value=config.get("talk", "CHANNELS"),
                    placeholder='Recording parameter.'
                )
                input_talk_silence_RATE = ui.input(
                    label='RATE',
                    value=config.get("talk", "RATE"),
                    placeholder='Recording parameter.'
                )

            
            with ui.card().style(card_css):
                ui.label("Google")
                with ui.grid(columns=1):
                    # Dropdown for selecting the target translation language
                    data_json = {}
                    for line in ["zh-CN", "en-US", "ja-JP"]:
                        data_json[line] = line
                    select_talk_google_tgt_lang = ui.select(
                        label='目标翻译语言', 
                        options=data_json, 
                        value=config.get("talk", "google", "tgt_lang")
                    ).style("width:200px")

            with ui.card().style(card_css):
                ui.label("Baidu")
                with ui.grid(columns=3):
                    # Input fields for Baidu API credentials
                    input_talk_baidu_app_id = ui.input(label='AppID', value=config.get("talk", "baidu", "app_id"), placeholder='AppID for Baidu Cloud Speech Recognition')
                    input_talk_baidu_api_key = ui.input(label='API Key', value=config.get("talk", "baidu", "api_key"), placeholder='API Key for Baidu Cloud Speech Recognition')
                    input_talk_baidu_secret_key = ui.input(label='Secret Key', value=config.get("talk", "baidu", "secret_key"), placeholder='Secret Key for Baidu Cloud Speech Recognition')

            with ui.card().style(card_css):
                ui.label("Faster Whisper")
                with ui.row():
                    # Input fields and dropdowns for Faster Whisper parameters
                    input_faster_whisper_model_size = ui.input(label='Model Size', value=config.get("talk", "faster_whisper", "model_size"), placeholder='Size of the model to use')
                    data_json = {}
                    for line in ["cuda", "cpu", "auto"]:
                        data_json[line] = line
                    select_faster_whisper_device = ui.select(
                        label='device', 
                        options=data_json, 
                        value=config.get("talk", "faster_whisper", "device")
                    ).style("width:200px")
                    data_json = {}
                    for line in ["float16", "int8_float16", "int8"]:
                        data_json[line] = line
                    select_faster_whisper_compute_type = ui.select(
                        label='compute_type', 
                        options=data_json, 
                        value=config.get("talk", "faster_whisper", "compute_type")
                    ).style("width:200px")
                    input_faster_whisper_download_root = ui.input(label='Download Root', value=config.get("talk", "faster_whisper", "download_root"), placeholder='Model download path')
                    input_faster_whisper_beam_size = ui.input(label='Beam Size', value=config.get("talk", "faster_whisper", "beam_size"), placeholder='The number of candidate sequences to consider at each step.')

            with ui.row():
                # Textarea for entering chat content
                textarea_talk_chat_box = ui.textarea(
                    label='ChatBox',
                    value="",
                    placeholder='Fill in the conversation content here to have a direct conversation (configure the chat mode earlier, remember to run it first)'
                ).style("width:500px;")

                # Functions related to the chat page
                '''
                Chat page related functions
                '''

                # Function to send chat box content
                def talk_chat_box_send():
                    global running_flag

                    if running_flag != 1:
                        ui.notify(position="top", type="info", message="Please click One-click to run before chatting")
                        return

                    # Get username and text content
                    user_name = input_talk_username.value
                    content = textarea_talk_chat_box.value

                    # Clear the chat box
                    textarea_talk_chat_box.value = ""

                    data = {
                        "type": "comment",
                        "platform": "webui",
                        "username": user_name,
                        "content": content
                    }

                    logging.debug(f"data={data}")

                    common.send_request(f'http://{config.get("api_ip")}:{config.get("api_port")}/send', "POST", data)

                # Function to directly echo (repeat) chat box content
                def talk_chat_box_reread():
                    global running_flag

                    if running_flag != 1:
                        ui.notify(position="top", type="info", message="Please click One-click to run before chatting")
                        return

                    # Get username and text content
                    user_name = input_talk_username.value
                    content = textarea_talk_chat_box.value

                    # Clear the chat box
                    textarea_talk_chat_box.value = ""

                    data = {
                        "type": "reread",
                        "username": user_name,
                        "content": content
                    }

                    common.send_request(f'http://{config.get("api_ip")}:{config.get("api_port")}/send', "POST", data)

                # Function to tune the chat box content for LLM
                def talk_chat_box_tuning():
                    global running_flag

                    if running_flag != 1:
                        ui.notify(position="top", type="info", message="Please click One-click to run before chatting")
                        return

                    # Get username and text content
                    user_name = input_talk_username.value
                    content = textarea_talk_chat_box.value

                    # Clear the chat box
                    textarea_talk_chat_box.value = ""

                    data = {
                        "type": "tuning",
                        "user_name": user_name,
                        "content": content
                    }

                    common.send_request(f'http://{config.get("api_ip")}:{config.get("api_port")}/send', "POST", data)

                # Buttons for sending, echoing, and tuning chat box content
                button_talk_chat_box_send = ui.button('Send', on_click=lambda: talk_chat_box_send(), color=button_internal_color).style(button_internal_css)
                button_talk_chat_box_reread = ui.button('Repeat', on_click=lambda: talk_chat_box_reread(), color=button_internal_color).style(button_internal_css)
                button_talk_chat_box_tuning = ui.button('Training', on_click=lambda: talk_chat_box_tuning(), color=button_internal_color).style(button_internal_css)

        
        with ui.tab_panel(assistant_anchor_page).style(tab_panel_css):
            with ui.row():
                switch_assistant_anchor_enable = ui.switch('Enable', value=config.get("assistant_anchor", "enable")).style(switch_internal_css)
                input_assistant_anchor_username = ui.input(label='Assistant Name', value=config.get("assistant_anchor", "username"), placeholder='Username for the assistant, currently not in use')
            with ui.card().style(card_css):
                ui.label("Trigger Types")
                with ui.row():
                    # Type list is derived from the supported 'type' values in audio_synthesis_handle audio synthesis
                    assistant_anchor_type_list = ["comment", "local_qa_audio", "song", "reread", "direct_reply", "read_comment", "gift", 
                                                "entrance", "follow", "idle_time_task"]
                    assistant_anchor_type_var = {}
                    
                    for index, assistant_anchor_type in enumerate(assistant_anchor_type_list):
                        if assistant_anchor_type in config.get("assistant_anchor", "type"):
                            assistant_anchor_type_var[str(index)] = ui.checkbox(text=assistant_anchor_type, value=True)
                        else:
                            assistant_anchor_type_var[str(index)] = ui.checkbox(text=assistant_anchor_type, value=False)
            with ui.grid(columns=4):
                switch_assistant_anchor_local_qa_text_enable = ui.switch('Enable Text Matching', value=config.get("assistant_anchor", "local_qa", "text", "enable")).style(switch_internal_css)
                select_assistant_anchor_local_qa_text_format = ui.select(
                    label='Storage Format',
                    options={'json': '自定义json', 'text': '一问一答'},
                    value=config.get("assistant_anchor", "local_qa", "text", "format")
                )
                input_assistant_anchor_local_qa_text_file_path = ui.input(label='Text Q&A Data Path', value=config.get("assistant_anchor", "local_qa", "text", "file_path"), placeholder='Local Q&A text data storage path').style("width:200px;")
                input_assistant_anchor_local_qa_text_similarity = ui.input(label='Minimum Text Similarity', value=config.get("assistant_anchor", "local_qa", "text", "similarity"), placeholder='Minimum text matching similarity. If lower, it will be treated as a regular danmaku').style("width:200px;")
            with ui.grid(columns=4):
                switch_assistant_anchor_local_qa_audio_enable = ui.switch('Enable Audio Matching', value=config.get("assistant_anchor", "local_qa", "audio", "enable")).style(switch_internal_css)
                select_assistant_anchor_local_qa_audio_type = ui.select(
                    label='Matching Algorithm',
                    options={'Contains': 'Contains', 'Similarity Match': 'Similarity Match'},
                    value=config.get("assistant_anchor", "local_qa", "audio", "type")
                )
                input_assistant_anchor_local_qa_audio_file_path = ui.input(label='Audio Storage Path', value=config.get("assistant_anchor", "local_qa", "audio", "file_path"), placeholder='Local Q&A audio file storage path').style("width:200px;")
                input_assistant_anchor_local_qa_audio_similarity = ui.input(label='Minimum Audio Similarity', value=config.get("assistant_anchor", "local_qa", "audio", "similarity"), placeholder='Minimum audio matching similarity. If lower, it will be treated as a regular danmaku').style("width:200px;")

        with ui.tab_panel(translate_page).style(tab_panel_css):
            with ui.row():
                switch_translate_enable = ui.switch('Enable', value=config.get("translate", "enable")).style(switch_internal_css)
                select_translate_type = ui.select(
                    label='Type', 
                    options={'baidu': 'Baidu Translate'}, 
                    value=config.get("translate", "type")
                ).style("width:200px;")
                select_translate_trans_type = ui.select(
                    label='Translation Type', 
                    options={'Danmaku': 'Danmaku', 'Reply': 'Reply', 'Danmaku+Reply': 'Danmaku+Reply'}, 
                    value=config.get("translate", "trans_type")
                ).style("width:200px;")
            with ui.card().style(card_css):
                ui.label("Baidu Translate")
                with ui.row():
                    input_translate_baidu_appid = ui.input(label='APP ID', value=config.get("translate", "baidu", "appid"), placeholder='Translation Open Platform Developer Center APP ID')
                    input_translate_baidu_appkey = ui.input(label='Key', value=config.get("translate", "baidu", "appkey"), placeholder='Translation Open Platform Developer Center Key')
                    select_translate_baidu_from_lang = ui.select(
                        label='Source Language', 
                        options={'auto': 'Auto Detect', 'zh': 'Chinese', 'cht': 'Traditional Chinese', 'en': 'English', 'jp': 'Japanese', 'kor': 'Korean', 'yue': 'Cantonese', 'wyw': 'Classical Chinese'}, 
                        value=config.get("translate", "baidu", "from_lang")
                    ).style("width:200px;")
                    select_translate_baidu_to_lang = ui.select(
                        label='Target Language', 
                        options={'zh': 'Chinese', 'cht': 'Traditional Chinese', 'en': 'English', 'jp': 'Japanese', 'kor': 'Korean', 'yue': 'Cantonese', 'wyw': 'Classical Chinese'}, 
                        value=config.get("translate", "baidu", "to_lang")
                    ).style("width:200px;")

                    
        with ui.tab_panel(web_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("WebUI Configuration")
                with ui.row():
                    input_webui_title = ui.input(label='Title', placeholder='Title of the WebUI', value=config.get("webui", "title")).style("width:250px;")
                    input_webui_ip = ui.input(label='IP Address', placeholder='IP address WebUI listens to', value=config.get("webui", "ip")).style("width:150px;")
                    input_webui_port = ui.input(label='Port', placeholder='Port WebUI listens to', value=config.get("webui", "port")).style("width:100px;")
                    switch_webui_auto_run = ui.switch('Auto Run', value=config.get("webui", "auto_run")).style(switch_internal_css)
                            
            with ui.card().style(card_css):
                ui.label("CSS")
                with ui.row():
                    theme_list = config.get("webui", "theme", "list").keys()
                    data_json = {}
                    for line in theme_list:
                        data_json[line] = line
                    select_webui_theme_choose = ui.select(
                        label='主题', 
                        options=data_json, 
                        value=config.get("webui", "theme", "choose")
                    )
                    
            with ui.card().style(card_css):
                ui.label("Account Management")
                with ui.row():
                    switch_login_enable = ui.switch('Login Functionality', value=config.get("login", "enable")).style(switch_internal_css)
                    input_login_username = ui.input(label='Username', placeholder='Your account, configured in config.json', value=config.get("login", "username")).style("width:250px;")
                    input_login_password = ui.input(label='Password', password=True, placeholder='Your password, configured in config.json', value=config.get("login", "password")).style("width:250px;")

        with ui.tab_panel(docs_page).style(tab_panel_css):
            with ui.row():
                ui.label('Online Documentation:')
                ui.link('https://luna.docs.ie.cx/', 'https://luna.docs.ie.cx/', new_tab=True)
            with ui.row():
                ui.label('NiceGUI Official Documentation:')
                ui.link('https://nicegui.io/documentation', 'https://nicegui.io/documentation', new_tab=True)
                
            ui.html('<iframe src="https://luna.docs.ie.cx/" width="1800" height="800"></iframe>').style("width:100%")
            
        with ui.tab_panel(about_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label('Introduction').style("font-size:24px;")
                ui.label('AI Vtuber is a virtual AI anchor that combines state-of-the-art technologies. Its core includes a series of efficient artificial intelligence models, including ChatterBot, GPT, Claude, langchain, chatglm, text-generation-webui, Xunfei Xinghuo, Zhipu AI, Google Bard, Wenxin Yiyuan, and Tongyi Xingchen. These models can run locally or be supported through cloud services.')
                ui.label('The appearance of AI Vtuber is created by combining Live2D, Vtube Studio, xuniren, and UE5 with the Audio2Face technology, providing users with a vivid and interactive virtual image. This enables AI Vtuber to engage in real-time interactive live broadcasts on major streaming platforms such as Bilibili, Douyin, Kuaishou, Douyu, YouTube, and Twitch. Of course, it can also engage in personalized conversations in a local environment.')
                ui.label('To make communication more natural, AI Vtuber uses advanced natural language processing technology combined with text-to-speech systems such as Edge-TTS, VITS-Fast, elevenlabs, bark-gui, VALL-E-X, Ruisheng AI, genshinvoice.top, and tts.ai-lab.top. This allows it to generate smooth responses and adjust its voice through so-vits-svc and DDSP-SVC to adapt to different scenes and roles.')
                ui.label('In addition, AI Vtuber can collaborate with Stable Diffusion through specific commands to showcase artworks. Users can also customize text, allowing AI Vtuber to play in a loop to meet different needs for various occasions.')
                
            with ui.card().style(card_css):
                ui.label('License').style("font-size:24px;")
                ui.label('This project is licensed under the GNU General Public License (GPL). For more information, please refer to the LICENSE file.')
                
            with ui.card().style(card_css):
                ui.label('Notice').style("font-size:24px;")
                ui.label('It is strictly forbidden to use this project for any purposes that violate the Constitution of the People\'s Republic of China, the Criminal Law of the People\'s Republic of China, the Public Security Administration Punishment Law of the People\'s Republic of China, and the Civil Code of the People\'s Republic of China.')
                ui.label('It is strictly prohibited for any political purposes.')
                
        with ui.grid(columns=6).style("position: fixed; bottom: 10px; text-align: center;"):
            button_save = ui.button('Save Configuration', on_click=lambda: save_config(), color=button_bottom_color).style(button_bottom_css)
            button_run = ui.button('One-Click Run', on_click=lambda: run_external_program(), color=button_bottom_color).style(button_bottom_css)
            button_stop = ui.button("Stop Running", on_click=lambda: stop_external_program(), color=button_bottom_color).style(button_bottom_css)
            button_light = ui.button('Turn Off Lights', on_click=lambda: change_light_status(), color=button_bottom_color).style(button_bottom_css)
            restart_light = ui.button('Restart', on_click=lambda: restart_application(), color=button_bottom_color).style(button_bottom_css)


    # Check if the auto-run feature is enabled
    if config.get("webui", "auto_run"):
        logging.info("Auto-run feature is enabled")
        run_external_program(type="api")

# Check if the login feature is enabled (currently not rational)
if config.get("login", "enable"):
    logging.info(config.get("login", "enable"))

    def my_login():
        username = input_login_username.value
        password = input_login_password.value

        if username == "" or password == "":
            ui.notify(position="top", type="info", message=f"Username or password cannot be empty")
            return

        if username != config.get("login", "username") or password != config.get("login", "password"):
            ui.notify(position="top", type="info", message=f"Incorrect username or password")
            return

        ui.notify(position="top", type="info", message=f"Login successful")

        label_login.delete()
        input_login_username.delete()
        input_login_password.delete()
        button_login.delete()
        button_login_forget_password.delete()

        login_column.style("")
        login_card.style("position: unset;")

        goto_func_page()

        return

    # @ui.page('/forget_password')
    def forget_password():
        ui.notify(position="top", type="info", message=f"Oops~ Forget it~o( =∩ω∩= )m")

    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(config.get("webui", "theme", "list", theme_choose, "login_card"))
        with login_card:
            label_login = ui.label('AI Vtuber').style("font-size: 30px;letter-spacing: 5px;color: #3b3838;")
            input_login_username = ui.input(label='Username', placeholder='Your account, configured in config.json', value="").style("width:250px;")
            input_login_password = ui.input(label='Password', password=True, placeholder='Your password, configured in config.json', value="").style("width:250px;")
            button_login = ui.button('Login', on_click=lambda: my_login()).style("width:250px;")
            button_login_forget_password = ui.button('Forget account/password?', on_click=lambda: forget_password()).style("width:250px;")
            # link_login_forget_password = ui.link('Forget account/password?', forget_password)

else:
    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(config.get("webui", "theme", "list", theme_choose, "login_card"))
        
        # Jump to the functional page
        goto_func_page()

ui.run(host=webui_ip, port=webui_port, title=webui_title, favicon="./ui/favicon-64.ico", language="zh-CN", dark=False, reload=False)