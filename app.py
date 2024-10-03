from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Whisper API ключ

# Instagram Scraper API параметры
instagram_scraper_api_url = "https://instagram-scraper-api2.p.rapidapi.com/v1.2/reels"
instagram_headers = {
    "x-rapidapi-key": "d45cca4414mshb086419fe90c9c1p124a57jsn53897848bfe7",
    "x-rapidapi-host": "instagram-scraper-api2.p.rapidapi.com"
}

# Маршрут для фильтрации и транскрибации аудиофайлов
@app.route('/process-links', methods=['POST'])
def process_links():
    # Получаем массив ссылок и минимальные просмотры из запроса
    data = request.json
    urls = data.get("urls", [])
    min_views = int(data.get("minViews", 100000))  # Используем значение по умолчанию, если minViews не указаны
    list_page = int(data.get("listPage", 20))
    er = float(data.get("er", 0.000000000000000000000000000003))
    proxy = data.get("proxy", None)  # Прокси передаётся через JSON-запрос

    # Настраиваем прокси, если они переданы
    proxies = None
    if proxy:
        proxies = {
            'http': proxy,
            'https': proxy
        }

    if not urls:
        print("Нет ссылок для обработки")
        return jsonify({"error": "No URLs provided"}), 400

    # Словарь для хранения отфильтрованных данных и транскрипций
    results = {}

    with open("filtered_links.txt", "w", encoding="utf-8") as links_file, \
            open("transcriptions.txt", "w", encoding="utf-8") as transcription_file:

        # Проходим по каждой ссылке
        for url in urls:
            try:
                querystring = {"username_or_id_or_url": url}
                pagination_token = None
                page_count = 0
                has_more_pages = True
                filtered_reels = []

                while has_more_pages and page_count < list_page:
                    if pagination_token:
                        querystring["pagination_token"] = pagination_token

                    # Используем прокси с авторизацией, если они указаны
                    response = requests.get(instagram_scraper_api_url, headers=instagram_headers, params=querystring, proxies=proxies)

                    if response.status_code != 200:
                        print(f"Ошибка запроса Instagram: {response.status_code}, {response.text}")
                        results[url] = {"error": f"Failed to fetch Instagram data, status code: {response.status_code}"}
                        break

                    data = response.json()

                    if 'data' in data and 'items' in data['data']:
                        for item in data['data']['items']:
                            play_count = item.get("play_count", 0)
                            reshare_count = item.get("reshare_count", 0)
                            code = item.get("code", "")

                            if play_count > min_views and (reshare_count * 100 / play_count) > er:
                                filtered_reels.append(
                                    {"code": f"https://instagram.com/reel/{code}", "caption": item["caption"]["text"],
                                     "url": item["video_url"]})

                    pagination_token = data.get("pagination_token")
                    has_more_pages = bool(pagination_token)

                    page_count += 1

                if filtered_reels:
                    for i, reel in enumerate(filtered_reels):
                        reel_url = reel['url']
                        reel_code = reel['code']
                        reel_caption = reel['caption']

                        try:
                            audio_response = requests.get(reel_url, proxies=proxies)

                            if audio_response.status_code == 200:
                                file_path = f"/tmp/reel_{i}.mp3"
                                with open(file_path, "wb") as audio_file:
                                    audio_file.write(audio_response.content)

                                whisper_url = "https://api.openai.com/v1/audio/transcriptions"
                                whisper_headers = {
                                    "Authorization": f"Bearer {api_key}",
                                }
                                with open(file_path, "rb") as audio_file:
                                    files = {"file": audio_file}
                                    whisper_data = {
                                        "model": "whisper-1",
                                        "language": "ru"
                                    }
                                    whisper_response = requests.post(whisper_url, headers=whisper_headers, files=files,
                                                                     data=whisper_data, proxies=proxies)

                                    if whisper_response.status_code == 200:
                                        transcription = whisper_response.json().get("text", "")
                                        results[url] = results.get(url, [])
                                        results[url].append({
                                            "reel_link": reel_code,
                                            "transcription": transcription,
                                            "description": reel_caption
                                        })

                                        transcription_file.write(f"Ролик: {reel_code}\n")
                                        transcription_file.write(f"Описание: {reel_caption}\n")
                                        transcription_file.write(f"Транскрипция:\n{transcription}\n\n")
                                    else:
                                        print(f"Ошибка транскрибации для ролика {reel_url}: {whisper_response.text}")
                                        results[url].append({
                                            "reel_link": reel_code,
                                            "transcription": f"Error transcribing {reel_url}: {whisper_response.text}",
                                            "description": reel_caption
                                        })

                                os.remove(file_path)

                            else:
                                print(f"Ошибка загрузки аудиофайла с {reel_url}: {audio_response.status_code}")
                                results[url].append({
                                    "reel_link": reel_code,
                                    "transcription": f"Error downloading {reel_url}: {audio_response.status_code}",
                                    "description": reel_caption
                                })

                        except Exception as e:
                            print(f"Ошибка обработки ролика {reel_url}: {str(e)}")
                            results[url].append({
                                "reel_link": reel_code,
                                "transcription": f"Error processing {reel_url}: {str(e)}",
                                "description": reel_caption
                            })

            except Exception as e:
                print(f"Ошибка обработки ссылки {url}: {str(e)}")

    print("Обработка завершена, отправка результатов...")
    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True)
