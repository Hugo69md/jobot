# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

class JobScraperPipeline:
    def process_item(self, item, spider):

        adapter = ItemAdapter(item)

        if adapter.get('URL') is None:
            raise DropItem("Missing URL in %s" % item)
        if adapter.get('name') is None: 
            raise DropItem("Missing name in %s" % item)
        if adapter.get('company') is None:
            raise DropItem("Missing company in %s" % item)
        if adapter.get('location') is None:
            raise DropItem("Missing location in %s" % item)
        if adapter.get('content') is None:
            raise DropItem("Missing content in %s" % item)
        
        if adapter.get('name') is not None:
            adapter['name'] = " ".join(adapter['name'].split())
        if adapter.get('company') is not None:
            adapter['company'] = " ".join(adapter['company'].split())
        if adapter.get('content') is not None:
            adapter['content'] = " ".join(adapter['content'].split())

        if adapter.get('URL') and not adapter.get('URL').startswith("http"):
            adapter['URL'] = spider.starts_urls[0] + adapter['URL']
        
        return item
