from bs4 import BeautifulSoup
import httpx
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/", methods=['POST', 'GET'])
def index():
    movie_data = {}
    noResults = ""
    search = request.args.get("search", " ")

    site_url = f'https://solidtorrents.net/library?q={search}&genres=all&rating=all&year=all&type=movie&countries=all&sort=popularity'
    response = httpx.get(site_url)
    source = response.text

    try:
        soup = BeautifulSoup(source, 'html.parser')
        container = soup.find('div', class_='movie-grid')
        all_movies = container.find_all(class_='w3-col')

        for details, movie in enumerate(all_movies):
            poster_chars = movie.find('div', 'poster-image').attrs['style'].replace('(', ' ')
            poster_chars = poster_chars.replace(')', ' ').split()
            poster = poster_chars[2]
            title = movie.find('h5', class_='title truncate')
            rating = movie.find('div', class_='bold').text
            rating = rating.replace('/', ' ')
            rating = rating.split()
            rating = rating[1]
            year = title.find_next_sibling("div")

            element = movie.find(class_='poster-overlay')
            div_element = element.find('div')
            div_element_next = div_element.find_next_sibling('div')
            category = div_element_next.find('a')
            link = movie.find('a').attrs['href']
            link = link.replace('/library/', '').replace('/', '%')

            movie_data.update({
                details: {
                    "movie_title": title.text,
                    "movie_poster": poster,
                    "movie_year": year.text,
                    "movie_rating": rating,
                    "movie_category": category.text,
                    "movie_link": link
                }
            })

            if title == "":
                noResults = "Nothing was found"
    except Exception:
        pass

    return render_template("index.html", movies=movie_data, noResults=noResults)


@app.route("/movie/<title>/")
def details(title):
    title = title.replace('%', '/')
    site_url = f'https://solidtorrents.net/library/{title}'
    response = httpx.get(site_url)
    source = response.text
    main_details = []
    download_links = {}
    API_TOKEN = "REAL-DEBRID-TOKEN"
    headers = {'Authorization': 'Bearer ' + API_TOKEN}

    try:
        soup = BeautifulSoup(source, 'html.parser')
        container = soup.find('div', class_='details-box view-box')
        poster_chars = container.find('div', 'poster-image hide-on-small').attrs['style'].replace('(', ' ')
        poster_chars = poster_chars.replace(')', ' ').split()
        poster = poster_chars[2]
        title_d = container.find('h5', class_='m-0 title')
        category_d = container.find('div', class_='link-1 primary-bg inline')
        extra_div = container.find('div', class_='inline-children primary-text lh-2')
        description_d = extra_div.find_next_sibling('div', class_='primary-text')

        second_container = container.find('div', class_='w3-row lh-1-5 primary-text')
        rating_d = second_container.find('div', class_='w3-col s12 m6 pb-05')
        runtime_d = rating_d.find_next_sibling('div', class_='w3-col s12 m6 pb-05')
        year_d = runtime_d.find_next_sibling('div', 'w3-col s12 m6 pb-05')
        country = year_d.find_next_sibling('div', 'w3-col s12 m6 pb-05')

        main_details.append(title_d.text)
        main_details.append(poster)
        main_details.append(category_d.text)
        main_details.append(description_d.text)
        main_details.append(rating_d.text)
        main_details.append(runtime_d.text)
        main_details.append(year_d.text)
        main_details.append(country.text)

        torrent_container = soup.find('div', class_='tab show')
        all_torrents = torrent_container.find_all(class_='search-result view-box')

        for stats, torrent in enumerate(all_torrents):
            magnet = torrent.find('a', class_='dl-magnet')
            magnet_title = torrent.find('h5', class_='title w-100 truncate')
            container_stats = torrent.find('div', class_='stats')
            downloads = container_stats.find('div')
            size = downloads.find_next_sibling('div')
            seeders = size.find_next_sibling('div')
            leechers = seeders.find_next_sibling('div')
            date = leechers.find_next_sibling('div')

            payload = {'magnet': magnet.attrs['href']}
            response = httpx.post("https://api.real-debrid.com/rest/1.0/torrents/addMagnet?",headers=headers, data=payload)
            data = response.json()
            torrent_id = data.get("id")

            payload = {'files': 1}
            response = httpx.post("https://api.real-debrid.com/rest/1.0/torrents/selectFiles/" + torrent_id, headers=headers, data=payload)

            response = httpx.get("https://api.real-debrid.com/rest/1.0/torrents/info/" + torrent_id, headers=headers)
            data = response.json()
            links = data.get("links")

            link_generated = ""
            for link in links:
                payload = {'link': link}
                response = httpx.post("https://api.real-debrid.com/rest/1.0/unrestrict/link?", headers=headers, data=payload)
                data = response.json()
                link_generated = data.get('download')

            download_links.update({
                stats: {
                    "magnet": link_generated,
                    "magnet_title": magnet_title.text,
                    "downloads": downloads.text,
                    "size": size.text,
                    "seeders": seeders.text,
                    "leechers": leechers.text,
                    "date": date.text
                }
            })

    except Exception:
        pass

    return render_template("details.html", movie=main_details, download_links=download_links)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
