function google(){
    url = document.getElementById('baidu')
    url.action = 'https://www.google.com/search'
    search = document.getElementById('change')
    search.name='q'
    text = document.getElementById("text")
    text.innerHTML = 'Google搜索'
}

function baidu() {
    url = document.getElementById('baidu')
    url.action = 'http://www.baidu.com/baidu'
    search = document.getElementById('change')
    search.name='Word'
    text = document.getElementById("text")
    text.innerHTML = 'Baidu搜索'

}