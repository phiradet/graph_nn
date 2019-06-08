# SET Crawler
A scrapy spider for scraping data from the official website of the Stock Exchange of Thailand (SET)


## Getting started
- Sample command
```bash
$ mkdir -p dataset/20190608/raw_data

$ scrapy crawl set_crawler \
    -a data_dir=$PWD/dataset/20190608/raw_data \
    -a mode=full \
    -L INFO \
    -o $PWD/dataset/20190608/20190608_SET_companies.jl \
    --logfile=$PWD/dataset/20190608/log
```

## Supported pages
- Company list: https://www.set.or.th/set/commonslookup.do?language=en&country=US
- Company profile: https://www.set.or.th/set/companyprofile.do?symbol=A&ssoPageId=4&language=en&country=US
- Company holder: https://www.set.or.th/set/companyholder.do?symbol=A&ssoPageId=6&language=en&country=US