""" В разделе каталога, который я выбрал случайно, я не смог найти
ни одной книжки с вариантами. Поэтому и в json файле их нет. На примере
обуви, допустим вот этой: 
https://www.wildberries.ru/catalog/14519740/detail.aspx?targetUrl=GP
для получения количества вариантов я бы написал что-то вроде:
options = selector.xpath('//div[@class="options"]//a').extract()
if options:
    len_options = len(options)
Также, я не смог найти товар не в наличии, поэтому, к сожалению, не смог
добавить это в выдачу. Было бы интересно узнать у лида, куда смотреть.
Не уверен, что догодка с переписыванием куки для указания региона
правильная, но другой я не нашел. Спасибо в любом случае."""

import re
import sys
import time

import scrapy

from scrapy.crawler import CrawlerProcess

sys.path.append(r'D:\\NewD\\scrapy_test\\scrapy\\test_parser')
from test_parser.items import ResultData


class TestParser(scrapy.Spider):
    name = 'TestScrapper'
    start_urls = [
        'https://www.wildberries.ru/catalog/knigi/detyam-i-roditelyam/obuchenie-chteniyu?page=%s' % page for page in range(1, 5)
    ]   
    
    result_data = ResultData()
    # Знаю, что костыль.
    section = None

    def start_requests(self):

        for url in self.start_urls:
            yield scrapy.Request(url=url,
                                 cookies={'__region':'68_33_75_70_63_69_48_30_1_4_40_31_22_38_71_65_66_64'},
                                 callback=self.parse,
                                 meta={'proxy': ''} #Вставить рабочий ip
        )

    def parse(self, response):

        selector = scrapy.Selector(response)
        item_urls = selector.xpath('//a[@class="ref_goods_n_p j-open-full-product-card"]/@href').extract()

        self.section = selector.xpath('//span[@itemprop="title"]/text()').extract()[1:]
        
        for url in item_urls:
            yield scrapy.Request(url, callback=self.parse_item_url)

    def parse_item_url(self, response):

        selector = scrapy.Selector(response)

        self.result_data['timestamp'] = time.time()
        self.result_data['RPC'] = selector.xpath('//span[@class="j-article"]/text()').get()
        self.result_data['url'] = response.request.url
        self.result_data['title'] = re.sub('[\"]', '', selector.xpath('//span[@class="name"]/text()').get())
        self.result_data['marketing_tags'] = selector.xpath('//a[@class="spec-actions-link"]/text()').extract()
        self.result_data['brand'] = selector.xpath('//span[@class="brand"]/text()').get()
        self.result_data['section'] = self.section[1:]

        current_price = selector.xpath('//span[@class="final-cost"]/text()').get()
        original_price = selector.xpath('//del[@class="c-text-base"]/text()').get()

        if current_price:
            clean_current_price = re.sub('[^0-9]', '', current_price)
        else:
            clean_current_price = 0

        if original_price:
            clean_original_price = re.sub('[^0-9]', '', original_price)
        else:
            clean_original_price = 0

        if clean_original_price !=0 and clean_current_price !=0:
            discount = round(100 - (int(clean_current_price) * 100) / int(clean_original_price), 2)
        else:
            discount = 0

        self.result_data['price_data'] = {'current': clean_current_price,
                                          'original': clean_original_price,
                                          'sale_tag': f'Скидка {discount} %'
        }

        view360 = selector.xpath('//a[@class="disabledZoom thumb_3d j-carousel-v360"]//img/@src').extract()

        self.result_data['assets'] = {'main_image': selector.xpath('//a[@class="j-carousel-image enabledZoom current"]//@src').extract(),
                                      'set_images': selector.xpath('//a[@class="j-carousel-image enabledZoom"]//@src').extract(),
                                      'view360': view360,
                                      'video': selector.xpath('//meta[@property="og:video"]/@content').extract()
        }

        parameters_names = selector.xpath('//div[@class="params"]//b/text()').extract()
        parameters_values = selector.xpath('//div[@class="params"]//span/text()').extract()

        clean_parameters_names = [re.sub('[\n"\+]', '', element) for element in parameters_names]
        clean_parameters_values = [re.sub('[\n"\+]', '', element) for element in parameters_values]

        description = selector.xpath('//div[@class="description j-collapsable-description i-collapsable-v1"]//p/text()').get()

        if description:
            clean_description = re.sub('[\n"\+]', '', description)
        else:
            clean_description = 'No description available on the web page'

        self.result_data['metadata'] = {'description': clean_description}

        for key, value in zip(clean_parameters_names, clean_parameters_values):
            self.result_data['metadata'][key] = value

        yield self.result_data


process = CrawlerProcess({
    'FEED_URI': 'result.json',
})

process.crawl(TestParser)
process.start()
