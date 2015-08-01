# -*- coding: utf-8 -*-
# splitfgdgmlschema.py
# begin     : 2015-07-31
# copyright : (C) 2015 Minoru Akagi
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
from xml.dom import minidom
from xml.etree import ElementTree

prefixMap = {'xs': 'http://www.w3.org/2001/XMLSchema'}

class FeatureType:

  def __init__(self, name, parent=None):
    self.name = name
    self.properties = []
    if parent:
      self.properties += parent.properties

  def addProperty(self, property):
    self.properties.append(property)

  def geometryProperty(self):
    for property in self.properties:
      if property.isGeometry():
        return property
    return None

  def exportToXsd(self, filename):
    elemName = self.name.replace('Type', '')

    with open(filename, 'w') as f:
      f.write(xsdHeader())
      f.write("""
	<xs:element name="{0}" type="fgd:{0}Type" substitutionGroup="gml:AbstractFeature"/>
	<xs:complexType name="{0}Type">
		<xs:complexContent>
			<xs:extension base="gml:AbstractFeatureType">
				<xs:sequence>
""".format(elemName))

      for property in self.properties:
        xsdType = property.toXsdType()
        if xsdType:
          f.write('					<xs:element name="{0}" type="{1}"/>\n'.format(property.name, xsdType))

      f.write("""				</xs:sequence>
			</xs:extension>
		</xs:complexContent>
	</xs:complexType>
""")
      f.write(xsdFooter())

  def exportToGfs(self, filename):
    doc = minidom.Document()

    root = doc.createElement('GMLFeatureClassList')
    doc.appendChild(root)

    parent = doc.createElement('GMLFeatureClass')
    root.appendChild(parent)

    elem = doc.createElement('Name')
    elemName = self.name.replace('Type', '')
    elem.appendChild(doc.createTextNode(elemName))
    parent.appendChild(elem)

    elem = doc.createElement('ElementPath')
    elem.appendChild(doc.createTextNode(elemName))
    parent.appendChild(elem)

    geomName = geomType = '[TODO] UNKNOWN'
    geom = self.geometryProperty()
    if geom:
      geomName = geom.name
      geomType = {'gml:PointPropertyType': 'Point',
                  'gml:CurvePropertyType': 'LineString',
                  'gml:SurfacePropertyType': 'Polygon'}.get(geom.type, '[TODO] UNKNOWN')

    elem = doc.createElement('GeometryElementPath')
    elem.appendChild(doc.createTextNode(geomName))
    parent.appendChild(elem)

    elem = doc.createElement('GeometryType')

    elem.appendChild(doc.createTextNode(geomType))
    parent.appendChild(elem)

    for property in self.properties:
      if property.isGeometry():
        continue

      gfsType = property.toGfsType()
      if not gfsType:
        continue

      pd = doc.createElement('PropertyDefn')
      parent.appendChild(pd)

      prop = doc.createElement('Name')
      prop.appendChild(doc.createTextNode(property.name))
      pd.appendChild(prop)

      prop = doc.createElement('ElementPath')
      prop.appendChild(doc.createTextNode(property.name))
      pd.appendChild(prop)

      prop = doc.createElement('Type')
      prop.appendChild(doc.createTextNode(gfsType))
      pd.appendChild(prop)

    with open(filename, 'w') as f:
      f.write('\n'.join(doc.toprettyxml('  ', '\n', 'utf-8').split('\n')[1:]))

  def print_(self):
    print self.name, self.properties

class FeatureProperty:

  def __init__(self, name, type):
    self.name = str(name)
    self.type = str(type)

  def isGeometry(self):
    return self.type in ['gml:PointPropertyType', 'gml:CurvePropertyType', 'gml:SurfacePropertyType']

  def toXsdType(self):
    if self.type.startswith('fgd:ref_'):    # reference
      return None

    if self.type.startswith('fgd:'):        # enumerated type
      return 'xs:string'

    return {'gml:TimeInstantType': 'xs:string'}.get(self.type, self.type)

  def toGfsType(self):
    if self.type.startswith('fgd:ref_'):    # reference
      return None

    if self.type.startswith('fgd:'):        # enumerated type
      return 'String'

    return {'xs:integer': 'Integer',
            'xs:double': 'Real',
            'xs:string': 'String',
            'gml:TimeInstantType': 'String'}.get(self.type, '[TODO] ' + self.type)

  def __repr__(self):
    return '"{0}": {1}'.format(self.name, self.type)

def splitFGDGMLschema(xsdPath, outputDir, outputType='xsd'):
  tree = ElementTree.parse(xsdPath)
  root = tree.getroot()

  featureTypes= {'gml:AbstractFeatureType': FeatureType('gml:AbstractFeatureType')}

  for element in root.findall('./xs:element', namespaces=prefixMap):
    print element.get('name'), element.get('type')

    typeName = element.get('type')
    subGroup = element.get('substitutionGroup')
    complexType = root.find('./xs:complexType[@name="{0}"]'.format(typeName.split(":")[-1]), namespaces=prefixMap)
    if not complexType:
      continue

    extension = complexType.find('.//xs:extension', namespaces=prefixMap)
    if not extension:
      continue

    featureType = FeatureType(typeName.split(":")[-1], featureTypes.get(extension.get('base')))
    for prop in complexType.findall('.//xs:element', namespaces=prefixMap):
      featureType.addProperty(FeatureProperty(prop.get('name'), prop.get('type')))

    featureTypes[typeName] = featureType

    featureType.print_()
    
    if outputType == 'gfs':
      featureType.exportToGfs(os.path.join(outputDir, 'jpfgdgml_{0}.gfs'.format(element.get('name'))))
    else:
      featureType.exportToXsd(os.path.join(outputDir, 'jpfgdgml_{0}.xsd'.format(element.get('name'))))

  return

def xsdHeader():
  return """<?xml version="1.0" encoding="utf-8"?>
<xs:schema targetNamespace="http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema"
	xmlns:fgd="http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema" 
	xmlns:gml="http://www.opengis.net/gml/3.2" 
	xmlns:xlink="http://www.w3.org/1999/xlink"
	xmlns:xs="http://www.w3.org/2001/XMLSchema"
	xmlns="http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema"
	elementFormDefault="qualified"
	attributeFormDefault="unqualified" >

	<xs:annotation>
		<xs:documentation>
			このファイルは次の国土地理院の基盤地図情報 ダウンロードデータ用 XML Schema定義文書をもとにしてGDAL(OGR)のGMLドライバで読み込めるように変更し、地物クラスごとに分割したものです.

			基盤地図情報 ダウンロードデータ用 XML Schema (XML Schema for Down Loaded Fundamental Geospatial Data)
			
			      (GML版) V4.0
			
			2008年3月 (March 2008)
			2014年7月改定 (Revised on July 2014)
			国土交通省国土地理院 (Geospatial Information Authority of Japan, Ministry of Land, Infrastructure, Transport and Tourism)
		</xs:documentation>
	</xs:annotation>

	<xs:import namespace="http://www.opengis.net/gml/3.2"
		 schemaLocation="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19136_Schemas/gml.xsd"/>

	<xs:element name="Dataset" type="DatasetType" substitutionGroup="gml:AbstractGML"/>
	<xs:complexType name="DatasetType">
		<xs:complexContent>
			<xs:extension base="gml:AbstractGMLType">
				<xs:sequence >
					<xs:element ref="gml:AbstractGML" maxOccurs="unbounded"/>
				</xs:sequence>
			</xs:extension>
		</xs:complexContent>
	</xs:complexType>
"""

def xsdFooter():
  return """
</xs:schema>
"""

if __name__ == '__main__':
  import sys
  outputType = 'gfs' if '-gfs' in sys.argv else 'xsd'
  splitFGDGMLschema('FGD_GMLSchema.xsd', 'output', outputType)
