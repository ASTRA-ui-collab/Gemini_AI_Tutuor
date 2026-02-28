from colorama import Fore, Style, init

try:
    from core import MODEL_CANDIDATES, SomaTutor, is_api_error_text
except ImportError:
    from .core import MODEL_CANDIDATES, SomaTutor, is_api_error_text

init(autoreset=True)


def choose_file(filetypes):
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Select file",
            filetypes=filetypes,
        )
        root.destroy()
        return selected or ""
    except Exception:
        return ""


def choose_image_file() -> str:
    return choose_file(
        [
            ("Image files", "*.jpg;*.jpeg;*.png;*.webp"),
            ("All files", "*.*"),
        ]
    )


def choose_audio_file() -> str:
    return choose_file(
        [
            ("Audio files", "*.wav;*.mp3;*.m4a;*.aac;*.flac;*.ogg"),
            ("All files", "*.*"),
        ]
    )


def banner() -> None:
    print(Fore.MAGENTA + Style.BRIGHT + "SOMA AI - Adaptive Multimodal Tutor")
    print(Fore.CYAN + f"Model candidates: {', '.join(MODEL_CANDIDATES)}")


def main() -> None:
    tutor = SomaTutor()
    banner()

    while True:
        print(Fore.YELLOW + "\n1. Ask Tutor")
        print("2. Summarize Text")
        print("3. Generate Quiz")
        print("4. Analyze Image / Transcribe Audio")
        print("5. Check Gemini Access")
        print("6. Exit")

        choice = input(Fore.GREEN + "\nSelect option: ").strip()

        if choice == "1":
            topic = input("Topic: ").strip()
            question = input("Question: ").strip()
            print(Fore.CYAN + "\nThinking...\n")
            answer = tutor.ask(topic, question)
            print(Fore.WHITE + answer)
            if not is_api_error_text(answer):
                tutor.update_progress(topic)
                if input("\nSave answer? (y/n): ").strip().lower() == "y":
                    path = tutor.save_note(answer)
                    print(Fore.GREEN + f"Saved to {path}")
            else:
                print(Fore.RED + "\nRequest failed; progress not updated and response will not be saved.")

        elif choice == "2":
            text = input("Paste text:\n")
            print(Fore.CYAN + "\nProcessing...\n")
            print(Fore.WHITE + tutor.summarize(text))

        elif choice == "3":
            topic = input("Quiz topic: ").strip()
            print(Fore.CYAN + "\nGenerating quiz...\n")
            print(Fore.WHITE + tutor.generate_quiz(topic))

        elif choice == "4":
            print("a. Analyze image")
            print("b. Transcribe lecture audio")
            sub = input("Select sub-option (a/b): ").strip().lower()

            if sub == "a":
                path = input("Enter image path (jpg/png/webp), or press Enter to browse: ").strip()
                if not path:
                    path = choose_image_file()
                    if not path:
                        print(Fore.RED + "No image selected.")
                        continue
                    print(Fore.CYAN + f"Selected: {path}")
                print(Fore.CYAN + "\nAnalyzing image...\n")
                print(Fore.WHITE + tutor.analyze_image(path))
            elif sub == "b":
                path = input("Enter audio path (wav/mp3/m4a/aac/flac/ogg), or press Enter to browse: ").strip()
                if not path:
                    path = choose_audio_file()
                    if not path:
                        print(Fore.RED + "No audio selected.")
                        continue
                    print(Fore.CYAN + f"Selected: {path}")
                print(Fore.CYAN + "\nTranscribing audio...\n")
                print(Fore.WHITE + tutor.transcribe_audio(path))
            else:
                print(Fore.RED + "Invalid sub-option.")

        elif choice == "5":
            print(Fore.CYAN + "\nRunning connectivity/model checks...\n")
            print(Fore.WHITE + tutor.check_access())

        elif choice == "6":
            print(Fore.MAGENTA + "Goodbye")
            break

        else:
            print(Fore.RED + "Invalid choice.")


if __name__ == "__main__":
    main()
