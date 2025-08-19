import cv2
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Event
import os
import sys
import logging
import subprocess
from datetime import datetime
import sp_save

#########################################################
# ログ出力設定　2025/07/24　　M.I
#########################################################
exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(exe_dir, 'app.log')
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#########################################################
# 録画クラス定義　2025/07/28　　M.I
#########################################################
class VideoRecorder:
    def __init__(self):
        self.frames = []
        self.recording_event = Event()
        self.recording_event.set()
        logging.info("録画クラスが初期化")

    #########################################################
    # 録画処理（スレッド内）　2025/07/28　　M.I
    #########################################################
    def record(self):
        logging.info("録画を開始")
        cv2.namedWindow('Recording... Press Stop to end.', cv2.WINDOW_NORMAL)
        cv2.moveWindow('Recording... Press Stop to end.', -10000, -10000)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logging.error("カメラが起動できませんでした。")
            error_root = tk.Tk()
            error_root.withdraw()
            tk.messagebox.showerror("カメラエラー", "起動できるカメラが存在しません。アプリケーションを終了します。")
            error_root.destroy()
            sys.exit(1)

        while self.recording_event.is_set() and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                self.frames.append(frame)
                cv2.imshow('Recording... Press Stop to end.', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logging.info("「q」キーが押されたため録画を終了")
                    break
            else:
                logging.warning("カメラからフレームの取得に失敗")
                break
        cap.release()
        cv2.destroyAllWindows()
        logging.info("録画が終了。取得フレーム数: %d", len(self.frames))

    #########################################################
    # 録画停止処理　2025/07/28　　M.I
    #########################################################
    def stop(self):
        self.recording_event.clear()
        logging.info("録画停止の指示を受け取り")

    #########################################################
    # 録画ファイル保存処理　2025/07/28　　M.I
    #########################################################
    def save(self):
        if not self.frames:
            logging.warning("録画されたフレームが存在しないため、保存をスキップ")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}_{user_name}.mp4"
        save_path = os.path.join(exe_dir, filename)

        height, width, _ = self.frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(save_path, fourcc, 10.0, (320, 240))
        for frame in self.frames:
            resized_frame = cv2.resize(frame, (320, 240))
            out.write(resized_frame)
        out.release()

        logging.info("録画ファイルを保存しました: %s", save_path)

        try:
            #subprocess.run([sys.executable, os.path.join(exe_dir, "sp_save.py"), save_path], check=True)

            if exe_dir not in sys.path:
                sys.path.append(exe_dir)
            sp_save.main(save_path)

            logging.info("sp_save.py を実行しました。ファイルパス: %s", save_path)
        except subprocess.CalledProcessError as e:
            logging.error("sp_save.py の実行に失敗しました: %s", e)

#########################################################
# グローバル変数定義
#########################################################
recorder = VideoRecorder()

#########################################################
# GUI停止ボタンのコールバック関数　2025/07/28　　M.I
#########################################################
def on_stop():
    global recorder
    recorder.stop()
    root.destroy()
    logging.info("停止ボタンがクリックされ、GUIを終了")
    recorder.save()

#########################################################
# 名前入力GUIの表示　2025/07/28　　M.I
#########################################################
def start_recording_with_name():
    global recorder, user_name
    user_name = name_entry.get().strip()
    if not user_name:
        messagebox.showwarning("入力エラー", "名前を入力してください。")
        return

    logging.info("ユーザー名が入力されました: %s", user_name)
    name_root.destroy()

    global root
    root = tk.Tk()
    root.title("録画コントロール")
    root.geometry("200x100")
    root.attributes('-topmost', True)

    stop_button = tk.Button(root, text="停止", command=on_stop, font=("Arial", 20), bg="red", fg="white")
    stop_button.pack(expand=True, fill='both')

    global recording_thread
    recording_thread = Thread(target=recorder.record)
    recording_thread.start()

    root.mainloop()

#########################################################
# 名前の入力GUI初期化　2025/07/28　　M.I
#########################################################
name_root = tk.Tk()
name_root.title("名前入力")
name_root.geometry("750x200")
name_root.attributes('-topmost', True)

tk.Label(name_root, text="\n名前を入力してください\n「進む」を押したあと、メールに記載のURLからテストを開始してください。\n", font=("Arial", 15)).pack(pady=5)
name_entry = tk.Entry(name_root, font=("Arial", 15))
name_entry.pack(pady=5)

start_button = tk.Button(name_root, text="進む", command=start_recording_with_name, font=("Arial", 15), bg="blue", fg="white")
start_button.pack(pady=5)

name_root.mainloop()
