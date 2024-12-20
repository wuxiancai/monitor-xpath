from lxml import html
import re
from difflib import SequenceMatcher

class XPathFinder:
    def __init__(self, tree):
        self.tree = tree
        
    def similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()
    
    def get_element_signature(self, element):
        """获取元素的特征"""
        signature = {
            'text': element.text_content().strip(),
            'tag': element.tag,
            'classes': element.get('class', ''),
            'id': element.get('id', ''),
        }
        return signature
        
    def find_similar_element(self, target_content):
        """根据内容查找最相似的元素"""
        best_match = None
        best_similarity = 0
        
        for element in self.tree.xpath('//*'):
            current = element.text_content().strip()
            similarity = self.similar(current, target_content)
            
            if similarity > best_similarity and similarity > 0.8:  # 80%相似度阈值
                best_similarity = similarity
                best_match = element
                
        return best_match
        
    def generate_xpath(self, element):
        """为元素生成XPath"""
        if element is None:
            return None
            
        # 尝试通过ID生成
        if element.get('id'):
            return f"//*[@id='{element.get('id')}']"
            
        # 尝试通过class生成
        if element.get('class'):
            classes = element.get('class').split()
            if classes:
                return f"//*[contains(@class, '{classes[0]}')]"
                
        # 生成完整路径
        path = []
        parent = element
        while parent is not None:
            siblings = parent.getparent().findall(parent.tag) if parent.getparent() is not None else []
            if len(siblings) > 1:
                index = siblings.index(parent) + 1
                path.insert(0, f"{parent.tag}[{index}]")
            else:
                path.insert(0, parent.tag)
            parent = parent.getparent()
            
        return '//' + '/'.join(path) 