def download_protocols():
    import requests
    from bs4 import BeautifulSoup
    import os

    url = "https://tangentsoft.com/rfcs/official.html"
    dir_name = "NetworkProtocols"
    parent_dir = "C:/Users/sarta/BigProjects/packto.ai"
    dir_path = os.path.join(parent_dir, dir_name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    with requests.Session() as session:
        response = session.get(url)
        response.raise_for_status()

        html_content = response.content

        soup = BeautifulSoup(html_content, 'html.parser')

        pdf_list = []

        for link in soup.find_all('a', href=True):
            if link['href'].endswith('txt'):
                pdf_list.append(link['href'])

        for pdf in pdf_list:
            if not pdf.startswith('http'):
                pdf = url + pdf

            try: 
                print(f"Downloading {pdf}")
                response = session.get(pdf)
                response.raise_for_status()

                file_name = pdf.split('/')[-1]
                file_path = os.path.join(dir_path, file_name)

                with open(file_path, 'wb') as f:
                    f.write(response.content)

            except requests.exceptions.RequestException as e:
                print(f"Failed to download {pdf}: {e}")

    print("COMPLETE")
