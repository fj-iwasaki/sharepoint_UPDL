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
import zipfile
import time

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
        self.recording_event = Event()
        self.recording_event.set()
        self.out = None
        logging.info("録画クラスが初期化")


    #########################################################
    # 録画処理（スレッド内）　2025/07/28　　M.I
    #########################################################
    def record(self):
        global save_path
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

        ret, frame = cap.read()
        if not ret:
            logging.error("初期フレームの取得に失敗")
            cap.release()
            return

        height, width, _ = frame.shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}_{user_name}.mp4"
        save_path = os.path.join(exe_dir, filename)
        self.out = cv2.VideoWriter(save_path, fourcc, 15.0, (320, 240))

        while self.recording_event.is_set() and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                resized_frame = cv2.resize(frame, (320, 240))

                # グレースケール化して保存
                gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
                gray_frame = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)  # 3chに戻す
                self.out.write(gray_frame)

                # self.out.write(resized_frame)
                cv2.imshow('Recording... Press Stop to end.', resized_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logging.info("「q」キーが押されたため録画を終了")
                    break
            else:
                logging.warning("カメラからフレームの取得に失敗")
                break

        cap.release()
        self.out.release()
        cv2.destroyAllWindows()
        logging.info("録画が終了。ファイル保存済み: %s", save_path)
        
        
        
        
        
        
        
        # ZIP化と sp_save 呼び出し（録画完了後）
        zip_path = os.path.splitext(save_path)[0] + ".zip"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(save_path, arcname=os.path.basename(save_path))
            logging.info("録画ファイルをZIP化しました: %s", zip_path)

            if exe_dir not in sys.path:
                sys.path.append(exe_dir)
            sp_save.show_upload_window(zip_path)
            logging.info("sp_save.py を実行しました。ファイルパス: %s", zip_path)
        except Exception as e:
            logging.error("ZIP化または sp_save.py の実行に失敗しました: %s", e)



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
        # if not self.frames:
        #     logging.warning("録画されたフレームが存在しないため、保存をスキップ")
        #     return

        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # filename = f"recording_{timestamp}_{user_name}.mp4"
        # save_path = os.path.join(exe_dir, filename)

        # height, width, _ = self.frames[0].shape
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # out = cv2.VideoWriter(save_path, fourcc, 10.0, (320, 240))
        # for frame in self.frames:
        #     resized_frame = cv2.resize(frame, (320, 240))
        #     out.write(resized_frame)
        # out.release()

        # logging.info("録画ファイルを保存しました: %s", save_path)


        for _ in range(10):
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                break
            time.sleep(0.5)

        # ZIPファイルのパスを作成
        zip_path = os.path.splitext(save_path)[0] + ".zip"

        # 録画ファイルをZIP化
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(save_path, arcname=os.path.basename(save_path))

        time.sleep(2)

        try:
            if exe_dir not in sys.path:
                sys.path.append(exe_dir)
            sp_save.show_upload_window(zip_path)
            logging.info("sp_save.py を実行しました。ファイルパス: %s", zip_path)
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
    # recorder.save()

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
    root.geometry("200x100+0+0")
    root.attributes('-topmost', True)
    root.overrideredirect(True)

    stop_button = tk.Button(root, text="停止", command=on_stop, font=("Arial", 20), bg="red", fg="white")
    stop_button.pack(expand=True, fill='both')
    stop_button.place(x=0, y=0, width=200, height=100)


    global recording_thread
    recording_thread = Thread(target=recorder.record)
    recording_thread.start()

    root.mainloop()

#########################################################
# 名前の入力GUI初期化　2025/07/28　　M.I
#########################################################
def show_name_input_window():
    def on_enter_key(event=None):
        start_recording_with_name()

    global name_root, name_entry

    name_root = tk.Tk()
    name_root.title("名前入力")

    # ウィンドウサイズと中央配置
    window_width = 750
    window_height = 350
    screen_width = name_root.winfo_screenwidth()
    screen_height = name_root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    name_root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    name_root.configure(bg="#2c3e50")
    name_root.resizable(False, False)
    name_root.attributes('-topmost', True)

    # ラベル
    label = tk.Label(
        name_root,
        text="\n名前を入力してください\n「進む」を押したあと、メールに記載のURLからテストを開始してください。\n",
        font=("Segoe UI", 16),
        fg="#ecf0f1",
        bg="#2c3e50"
    )
    label.pack(pady=10)

    # 入力欄
    name_entry = tk.Entry(name_root, font=("Segoe UI", 18), justify="center")
    name_entry.pack(pady=10)
    name_entry.focus_set()  # 初期フォーカス

    # ボタン
    start_button = tk.Button(
        name_root,
        text="▶ 進む",
        command=start_recording_with_name,
        font=("Segoe UI", 16, "bold"),
        bg="#3498db",
        fg="white",
        activebackground="#2980b9",
        activeforeground="white",
        width=15,
        height=1
    )
    start_button.pack(pady=10)

    # Enterキーで進む
    name_root.bind('<Return>', on_enter_key)

    name_root.mainloop()

if __name__ == "__main__":
    show_name_input_window()
