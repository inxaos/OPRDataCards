import io
import platform
import subprocess
from PIL import Image, ImageDraw
from reportlab.lib import utils
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import sys
import os
import urllib.request
import time
import stat
import json
import re
import click
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import pathlib
import requests
import zipfile
import logging
import tkinter as tk
from tkinter import ttk, filedialog
import os
import platform
import subprocess
import threading
from dataclasses import dataclass


logger = logging.getLogger(__name__)


# Erstelle einen benutzerdefinierten Handler
class CustomHandler(logging.Handler):
    def __init__(self, log_format):
        super().__init__()
        # Initialisiere den Formatter im Handler
        self.formatter = logging.Formatter(log_format)

    def emit(self, record):
        if record.levelname == "INFO":
            log_status(record.getMessage())
        else:
            # Formatiere die Log-Nachricht
            formatiertes_log = self.format(record)
            # Ruf die Funktion auf, wenn eine Log-Nachricht gesendet wird
            log_status(formatiertes_log)


@click.command()
@click.option(
    "-f",
    "--file",
    "armyFile",
)
@click.option(
    "--debug / --no-debug",
    "debugOutput",
    default=False,
    required=False
)
@click.option(
    "--validate / --no-validate",
    "validateVersion",
    default=True,
    required=False
)
@click.option(
    "--2w6 / --w6",
    "_2w6",
    default=False,
    required=False
)

def Main(armyFile, debugOutput, validateVersion, _2w6):
    set_settings(debugOutput, validateVersion, _2w6)
    conf_logging()
    if not createStructure():
        waitForKeyPressAndExit()
    checkFonts()

    if armyFile is None:
        gui_mode()
    else:
        settings['gui'] = False
        cli(armyFile)

def gui_mode():
    root = gui_create()
    settings['gui'] = True
    root.after(0, select_file)
    root.mainloop()

def set_settings(debugOutput, validateVersion,_2w6):
    basePath = get_base_path()
    dataFolder = os.path.join(basePath, "data")
    imageFolder = os.path.join(dataFolder, "images")
    global settings
    settings = {
        'gui': False,
        'validateVersion': validateVersion,
        'path': {
            'dataFolder': dataFolder,
            'dataFolderArmyBook': os.path.join(dataFolder, "armybook"),
            'fontFolder': os.path.join(dataFolder, "fonts"),
            'dataCardFolder': os.path.join(dataFolder, "datacards"),
            'imageFolder': imageFolder,
            'imageJson': os.path.join(imageFolder, "images.json"),
        },
        'debug': debugOutput,
        '2w6': _2w6,
    }

def conf_logging():
    log_format = "%(levelname)10s [%(lineno)5s - %(funcName)30s() ] %(message)s"
    logger = logging.getLogger(__name__)
    logging.basicConfig(format=log_format)
    custom_handler = CustomHandler(log_format)
    logger.addHandler(custom_handler)

    if settings['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

def get_base_path():
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)

def cli(armyFile):
    processArmyFile(armyFile)

def processArmyFile(armyFile: str):
    typeJson = isFileTypeJson(armyFile)
    army = None
    if (typeJson == True):
        logger.debug("Parse json army file")
        try:
            army = parseArmyJsonList(armyFile, settings['validateVersion'])
        except Exception as ex:
            logger.error("General Parsing error")
            logger.error(ex)
            return
    else:
        logger.debug("Parse txt army file")
        txtData = readTxtFile(armyFile)
        army = parseArmyTextList(txtData)
    if army != None and army != False:
        if logger.level == logging.DEBUG:
            file = os.path.join(settings['path']['dataFolder'], "debug_army.json")
            logger.info("Save debug file {file}")
            saveDictToJson(army, file)

        pdfFile = createDataCard(army)
        openFile(pdfFile)

def isFileTypeJson(file):
    if file != None and file != "":
        suffixes = pathlib.Path(file).suffixes
        if (suffixes[len(suffixes) - 1].lower() == ".json"):
            return True
    return False


def readTxtFile(file):
    try:
        f = open(file, "r")
        txtData = f.read().split("\n")
        f.close()
    except Exception as ex:
        logger.error("Error Reading test txt file " + str(ex))
    return txtData


def fileSelectDialog():
    Tk().withdraw()
    return askopenfilename()


def createStructure():
    logger.debug(f'Check data structure')
    if not os.path.exists(settings['path']['dataFolder']):
        try:
            os.makedirs(settings['path']['dataFolder'])
        except Exception as ex:
            logger.error("Data folder creation failed")
            logger.error(ex)
            return False

    if not os.path.exists(settings['path']['dataFolderArmyBook']):
        try:
            os.makedirs(settings['path']['dataFolderArmyBook'])
        except Exception as ex:
            logger.error("army book folder creation failed")
            logger.error(ex)
            return False

    if not os.path.exists(settings['path']['fontFolder']):
        try:
            os.makedirs(settings['path']['fontFolder'])
        except Exception as ex:
            logger.error("font folder creation failed")
            logger.error(ex)
            return False

    if not os.path.exists(settings['path']['imageFolder']):
        try:
            os.makedirs(settings['path']['imageFolder'])
        except Exception as ex:
            logger.error("image folder creation failed")
            logger.error(ex)
            return False

    if not os.path.exists(settings['path']['dataCardFolder']):
        try:
            os.makedirs(settings['path']['dataCardFolder'])
        except Exception as ex:
            logger.error("datacard folder creation failed")
            logger.error(ex)
            return False

    if not os.path.exists(settings['path']['imageJson']):
        example = [
            {
                'listName': '*',
                'armyFaction': 'Human Defense Force',
                'unitType': 'Company Leader',
                'unitName': '*',
                'weaponOrEquipment': "*",
                'images': 'example.jpg',
            },
            {
                'listName': '*',
                'armyFaction': '*',
                'unitType': '*',
                'unitName': 'Herg Alasem',
                'weaponOrEquipment': "*",
                'images': ['example.jpg'],
            },
            {
                'listName': '*',
                'armyFaction': '*',
                'unitType': 'Storm Trooper',
                'unitName': '*',
                'weaponOrEquipment': "Flamer",
                'images': ['example.jpg'],
            },
            {
                'listName': '*',
                'armyFaction': '*',
                'unitType': 'Storm Trooper',
                'unitName': '*',
                'weaponOrEquipment': "*",
                'images': ['example1.jpg', 'example2.jpg'],
            },
        ]
        saveDictToJson(example, os.path.join(settings['path']['imageJson']))
    
    return True


def openFile(filePath):
    if platform.system() == 'Darwin':
        subprocess.call(('open', filePath))
    elif platform.system() == 'Windows':
        os.startfile(filePath)
    else:
        subprocess.call(('xdg-open', filePath))


def dataCardBoarderFrame(pdf, dataCardParameters):
    pdf.setStrokeColorRGB(dataCardParameters['lineColor'][0],
                          dataCardParameters['lineColor'][1], dataCardParameters['lineColor'][2])
    path = pdf.beginPath()
    path.moveTo(0 + dataCardParameters['sideClearance'], 0 + dataCardParameters['bottomClearance'])
    path.lineTo(0 + dataCardParameters['sideClearance'],
                dataCardParameters['pdfSize'][1] - dataCardParameters['topClearance'])
    path.lineTo(dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance'],
                dataCardParameters['pdfSize'][1] - dataCardParameters['topClearance'])
    path.lineTo(dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance'],
                0 + dataCardParameters['bottomClearance'])
    path.close()
    pdf.setLineJoin(1)
    pdf.drawPath(path, stroke=1, fill=0)

def getUnitCost(unit):
    cost = unit['cost']
    if 'upgradeCost' in unit:
        for addCost in unit['upgradeCost']:
            cost += addCost
    return cost

def dataCardUnitPoints(pdf, dataCardParameters, unit):
    if 'cost' in unit:
        startX = (dataCardParameters['pdfSize'][0] / 2) + 35
        startY = dataCardParameters['pdfSize'][1] - 47
        pdf.setFont('regular', 8)
        pdf.setFillColorRGB(0, 0, 0)

        cost = getUnitCost(unit)

        sideClearance = 20
        bottomClearance = 5
        height = 10
        pdf.setFont('regular', 7)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawRightString(dataCardParameters['pdfSize'][0] - 22, bottomClearance +
                            (height/2)-2, str(cost) + " pt")

def process_rules_list(rules_list):
    toughPattern = re.compile(r"Tough\((\d+)\)")
    global total_tough
    new_rules = []
    #logger.info(rules_list)
    for rule in rules_list:
        match = toughPattern.match(rule)
        if match and total_tough is int :
            total_tough += int(match.group(1))
            # Skip this rule (we're aggregating it)
        elif match :
             total_tough = int(match.group(1))
        else:
            new_rules.append(rule)
    return new_rules

def dataCardUnitType(pdf, dataCardParameters, unit):
    # Unit type
    pdf.line(dataCardParameters['sideClearance'], dataCardParameters['pdfSize'][1] - 50,
             dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance'], dataCardParameters['pdfSize'][1] - 50)
    smallInfo = []
    # if (unit['size'] > 1):
    #     smallInfo.append(str(unit['size']) + "x")

    if 'type' in unit and unit['name'] != unit['type']:
            #pdf.setFont('bold', 7)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(5, dataCardParameters['pdfSize'][1] - 47, " ".join(smallInfo))
        smallInfo.append(unit['type'])

    sideClearance = 20
    height = 10
    bottomClearance = 5
    specialRules = []
    for rule in unit['rules']:
        #logger.info(rule)
        count = ""
        if 'count' in rule and unit['size'] != 1:
            count = f'{rule["count"]}x '
        specialRules.append(f'{count}{rule["label"]}')

    for equip in unit['equipment']:
        #logger.info(equip)
        # count = ""
        # if 'count' in equip and unit['size'] != 1:
        #     count = f'{equip["count"]}x '
        #specialRules.append(f'{count}{equip['specialRule']["label"]}')
        for sr in equip['specialRules']:
            if sr['label'] not in specialRules:
                specialRules.append(f'{sr["label"]}')

    #Additive toughness
    
    #total_tough = 0

    #for unit in army['units']:
    # Process unit-level rules
    #logger.info(specialRules)
    global total_tough
    total_tough = 0
    processedRules = process_rules_list(specialRules)
    #logger.info(processedRules)

    # Process weapon-level rules
    # for weapon in unit.get('weapons', []):
    #     weapon['specialRules'] = process_rules_list(weapon.get('specialRules', []))

    # # Process equipment-level rules
    # for equipment in unit.get('equipment', []):
    #     equipment['specialRules'] = process_rules_list(equipment.get('specialRules', []))



    nameLines = []
    maxLineChars = 55
    lineParts = []
    parts = ", ".join(specialRules).split(" ")
    for part in parts:
        if len(" ".join(lineParts)) + len(part) > maxLineChars:
            nameLines.append(" ".join(lineParts))
            lineParts = []
        lineParts.append(part)
    nameLines.append(" ".join(lineParts))

    pdf.setFont('bold', 7)
    pdf.setFillColorRGB(0, 0, 0)
    offset = 0
    if len(nameLines) > 1:
        offset -= 12
    for line in nameLines:
        #pdf.drawString(5, dataCardParameters['pdfSize'][1] - 25 - offset, line)
        pdf.drawString(5, dataCardParameters['pdfSize'][1] - 47 - offset, line)
        offset += 10
    
    #smallInfo.append(", ".join(specialRules))

    #pdf.setFont('bold', 7)
    #pdf.setFillColorRGB(0, 0, 0)
    #pdf.drawString(5, dataCardParameters['pdfSize'][1] - 47, " ".join(smallInfo))


def dataCardUnitWounds(pdf, dataCardParameters, unit, army):
    if 'gameSystem' in army and army['gameSystem'] == "gff":
        woundsSize = 12
        wounds = 5
        tough = 0
        startX = 2
        startY = dataCardParameters['pdfSize'][1] - 50 - woundsSize
        for rule in unit['rules']:
            if (rule['name'].lower() == "tough"):
                tough = int(rule['rating']) - 1

        pdf.setLineJoin(1)
        pdf.setFillColorRGB(0.5, 0.5, 0.5)
        path = pdf.beginPath()
        path.moveTo(startX, startY)
        path.lineTo(startX + (woundsSize * tough), startY)
        path.lineTo(startX + (woundsSize * tough), startY + woundsSize)
        path.lineTo(startX, startY + woundsSize)
        path.close()
        pdf.drawPath(path, stroke=1, fill=0)

        path = pdf.beginPath()
        path.moveTo(startX + (woundsSize * tough), startY)
        path.lineTo(startX + (woundsSize * tough) + (woundsSize * wounds), startY)
        path.lineTo(startX + (woundsSize * tough) + (woundsSize * wounds), startY + woundsSize)
        path.lineTo(startX + (woundsSize * tough), startY + woundsSize)

        path.close()
        pdf.drawPath(path, stroke=1, fill=1)

        if settings['2w6']:
            dice = 8
        else:
            dice = 5
        for i in range(wounds + tough):
            pdf.line(startX + (woundsSize*i), startY, startX + (woundsSize*i), startY + woundsSize)
            pdf.setFillColorRGB(1, 1, 1)

            if (i < tough):
                text = "-"
            else:
                text = str(dice) + "+"
                dice -= 1
            pdf.drawCentredString(startX + (woundsSize*i) + (woundsSize/2), startY + (woundsSize/2) - 3, text)


def dataCardUnitRules(pdf, dataCardParameters, unit):
    pdf.setStrokeColorRGB(dataCardParameters['lineColor'][0],
                          dataCardParameters['lineColor'][1], dataCardParameters['lineColor'][2])
    pdf.setFillColorRGB(1, 1, 1)
    path = pdf.beginPath()
    sideClearance = 20
    height = 10
    bottomClearance = 5

    path.moveTo(0 + sideClearance, 0 + bottomClearance)
    path.lineTo(dataCardParameters['pdfSize'][0] - sideClearance, 0 + bottomClearance)
    path.lineTo(dataCardParameters['pdfSize'][0] - sideClearance,
                0 + bottomClearance + height)
    path.lineTo(0 + sideClearance, 0 + bottomClearance + height)
    path.close()
    pdf.setLineJoin(1)
    pdf.drawPath(path, stroke=1, fill=1)
    pdf.setFont('bold', 7)
    pdf.setFillColorRGB(0, 0, 0)

    specialRules = []
    #logger.debug("CHECK")
    #logger.idebugnfo(unit)
    for rule in unit['rules']:
        logger.debug(rule)
        count = ""
        if 'count' in rule and unit['size'] != 1:
            count = f'{rule["count"]}x '
        specialRules.append(f'{count}{rule["label"]}')

    #TODO: Add Quality Def Toughness AND/OR Quest Stats here
    #pdf.drawString(sideClearance+2, bottomClearance + (height/2)-2, ", ".join(specialRules))

    # nameLines = []
    # maxLineChars = 25
    # lineParts = []
    # parts = ", ".join(specialRules).split(" ")
    # for part in parts:
    #     if len(" ".join(lineParts)) + len(part) > maxLineChars:
    #         nameLines.append(" ".join(lineParts))
    #         lineParts = []
    #     lineParts.append(part)
    # nameLines.append(" ".join(lineParts))

    # pdf.setFont('bold', 14)
    # pdf.setFillColorRGB(0, 0, 0)
    # offset = 0
    # for line in nameLines:
    #     #pdf.drawString(5, dataCardParameters['pdfSize'][1] - 25 - offset, line)
    #     pdf.drawString(sideClearance+2, bottomClearance + (height/2)-2 - offset, line)
    #     offset += 12

    #pdf.drawString(sideClearance+2, bottomClearance + (height/2)-2, ", ".join(specialRules))

def dataCardUnitImage(pdf, dataCardParameters, unit, listName, armyFaction, imageInfos):
    if imageInfos == False:
        return


    logger.debug(f'Get image')
    logger.debug(f'listName:  {listName}')
    logger.debug(f'armyFaction:  {armyFaction}')
    unit_images = None
    for image_index in range(0, len(imageInfos)):
        imageInfo = imageInfos[image_index]
        if imageInfo['unitName'] == "*" or re.search(r'(?is)' + imageInfo['unitName'], unit['name'].strip()):
            if imageInfo['unitType'] == "*" or re.search(r'(?is)' + imageInfo['unitType'], unit['type'].strip()):
                if imageInfo['listName'] == "*" or re.search(r'(?is)' + imageInfo['listName'], listName.strip()):
                    if imageInfo['armyFaction'] == "*" or re.search(r'(?is)' + imageInfo['armyFaction'], armyFaction.strip()):
                        if imageInfo['weaponOrEquipment'] == "*":
                            unit_images = imageInfo['images']
                        else:
                            for weapon in unit['weapons']:
                                if re.search(r'(?is)' + imageInfo['weaponOrEquipment'], weapon['name'].strip()):
                                    unit_images = imageInfo['images']

                            if 'equipment' in unit:
                                for equipment in unit['equipment']:
                                    if re.search(r'(?is)' + imageInfo['weaponOrEquipment'], equipment['name'].strip()):
                                        unit_images = imageInfo['images']

                            if 'rules' in unit:
                                for rules in unit['rules']:
                                    if re.search(r'(?is)' + imageInfo['weaponOrEquipment'], rules['name'].strip()):
                                        unit_images = imageInfo['images']

                        if unit_images is not None:
                            logger.debug(f'Match {image_index}: {unit_images}')
                            break
    
    unit_image = None
    if unit_images is not None:
        if len(unit_images) == 1: # Only one image
            unit_image = unit_images[0]['file']
            unit_images[0]['used'] += 1
        elif len(unit_images) > 1: # Multiple images
            lowest_use_index = -1
            for index in range(0, len(unit_images)):
                if lowest_use_index == -1:
                    lowest_use_index = index
                elif unit_images[index]['used'] < unit_images[lowest_use_index]['used']:
                    lowest_use_index = index
            unit_image = unit_images[lowest_use_index]['file']
            unit_images[lowest_use_index]['used'] += 1

        if unit_images is not None:
            unit_image = os.path.join(settings['path']['imageFolder'], unit_image)
            if not os.path.exists(unit_image):
                logger.warning(f'Image not found: {unit_image}')

                unit_image = None


    if (unit_image != None):
        with Image.open(unit_image) as img:
            img.load()
            imgSize = img.size
            draw = ImageDraw.Draw(img)
            draw.polygon(((0, 0), (imgSize[0]/2, imgSize[1]),
                          (0, imgSize[1])), fill=(0, 255, 0))
            draw.polygon(((imgSize[0], 0), (imgSize[0]/2, imgSize[1]),
                          (imgSize[0], imgSize[1])), fill=(0, 255, 0))
            imageBuffer = io.BytesIO()
            img.save(imageBuffer, "png")
            imageBuffer.seek(0)

    edgeLength = 65
    offsetTop = 2
    offsetRight = 40
    triangle = [
        [dataCardParameters['pdfSize'][0] - edgeLength - offsetRight,
            dataCardParameters['pdfSize'][1] - offsetTop],
        [dataCardParameters['pdfSize'][0] - offsetRight, dataCardParameters['pdfSize'][1] - offsetTop],
        [dataCardParameters['pdfSize'][0] - (edgeLength/2) - offsetRight,
         dataCardParameters['pdfSize'][1] - offsetTop - edgeLength]
    ]

    pdf.setStrokeColorRGB(dataCardParameters['lineColor'][0],
                          dataCardParameters['lineColor'][1], dataCardParameters['lineColor'][2])
    if (unit_image != None):
        pdf.drawImage(utils.ImageReader(imageBuffer), dataCardParameters['pdfSize'][0] - offsetRight - edgeLength,
                      dataCardParameters['pdfSize'][1] - offsetTop - edgeLength, edgeLength, edgeLength, mask=[0, 0, 255, 255, 0, 0])
        fillPath = 0
    else:
        fillPath = 1
    path = pdf.beginPath()
    path.moveTo(triangle[0][0], triangle[0][1])
    path.lineTo(triangle[1][0], triangle[1][1])
    path.lineTo(triangle[2][0], triangle[2][1])
    path.close()
    pdf.setLineJoin(1)
    pdf.setFillColorRGB(0.7, 0.7, 0.7)
    pdf.drawPath(path, stroke=1, fill=fillPath)


def dataCardUnitName(pdf, dataCardParameters, unit):
    logger.info(unit)
    fontSize = 14
    maxLineChars = 25
    if len(unit['name']) > 25:
        fontSize = 12
        maxLineChars = 35
    # Unit Name
    parts = unit['name'].split(" ")
    nameLines = []
    #maxLineChars = 25
    lineParts = []
    for part in parts:
        if len(" ".join(lineParts)) + len(part) > maxLineChars:
            nameLines.append(" ".join(lineParts))
            lineParts = []
        lineParts.append(part)
    if int(unit['size']) > 1:
        lineParts.append(" (x" + str(unit['size']) + ")")
    nameLines.append(" ".join(lineParts))

    #pdf.setFont('bold', 14)
    pdf.setFont('bold', fontSize)
    pdf.setFillColorRGB(0, 0, 0)
    offset = 0
    for line in nameLines:
        pdf.drawString(5, dataCardParameters['pdfSize'][1] - 25 - offset, line)
        offset += 12

def dataCardArmyBookVersion(pdf, dataCardParameters, versions, armyId):
    logger.debug("Add version")

    version = None
    for check in versions:
        if armyId == check['armyId']:
            version = check['version']
    if version is None:
        return
         
    pdf.setFont('bold', 4)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawRightString(dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance'],
                0 + dataCardParameters['bottomClearance'] -6, version)

def dataCardUnitSkills(pdf, dataCardParameters, unit):
    startX = dataCardParameters['pdfSize'][0] - 25
    startY = dataCardParameters['pdfSize'][1] - 26
    lineHight = 8
    quality = getDiceRoll(unit["quality"], settings['2w6'])
    defense = getDiceRoll(unit["defense"], settings['2w6'])
    pdf.setFont('bold', 12)
    #pdf.setFillColorRGB(0, 0, 0)
    pdf.setFillColorRGB(0, 0.4375, 0)
    pdf.drawCentredString(startX, startY, "Qua: " + str(quality) + "+")
    pdf.setFillColorRGB(0.74609375, 0.0859375, 0)
    pdf.drawCentredString(startX, startY - (lineHight*2), "Def:  " + str(defense) + "+")
    #pdf.setFont('regular', 8)
    # pdf.setFillColorRGB(0.74609375, 0.0859375, 0)
    # pdf.drawCentredString(startX, startY - (lineHight*1), str(quality) + "+")
    # pdf.setFillColorRGB(0, 0.4375, 0)
    # pdf.drawCentredString(startX, startY - (lineHight*3), str(defense) + "+")
    pdf.setFillColorRGB(0, 0, 0)


def dataCardUnitWeaponsEquipment(pdf, dataCardParameters, unit):
    # Weapon
    startX = 5
    startY = dataCardParameters['pdfSize'][1] - 75
    offsetX = [0, 130, 155, 180, 200]
    offsetY = 0
    headers = ['Weapon', 'Rng', 'Atk', 'AP', 'Special Rules']
    color = 1

    for i in range(len(headers)):
        pdf.setFont("bold", 10)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(startX + offsetX[i], startY + offsetY, headers[i])
    offsetY -= 12

    sortedWeapons = sorted(unit['weapons'], 
        key=lambda w: (
            int(w.get('range', 0)),
            int(w.get('attacks', 0)),
            int(w.get('ap', 0)),
            int(w.get('count', 0))
        )
    )

    for weapon in sortedWeapons:
        pdf.setFont("regular", 10)

        #highlight alternating rows
        if color == 1:
           color = 0.7421875
        else:
           color = 1

        pdf.saveState() 
        pdf.setFillColorRGB(color, color, color)
        pdf.setStrokeColorRGB(color,color,color)
        pdf.rect(startX + offsetX[0],startY + offsetY - 2,290,10, fill=1)
        pdf.restoreState() 

        pdf.setFillColorRGB(0, 0, 0)
        if int(weapon['count']) > 1:
            weaponLabel = str(weapon['count']) + "x " + weapon['name']
        else:
            weaponLabel = weapon['name']

        pdf.drawString(startX + offsetX[0],
                       startY + offsetY, weaponLabel)

        if "range" in weapon:
            pdf.drawString(startX + offsetX[1] + 5, startY + offsetY, str(weapon['range']) + '"')
        else:
            pdf.drawString(startX + offsetX[1] + 7, startY + offsetY, "-")

        pdf.drawString(startX + offsetX[2] + 2, startY + offsetY, "A" + str(weapon['attacks']))

        if "ap" in weapon:
            pdf.drawString(startX + offsetX[3] + 5, startY +
                           offsetY, str(weapon['ap']))
        else:
            pdf.drawString(startX + offsetX[3] + 5, startY + offsetY, "-")

        if "specialRules" in weapon and len(weapon['specialRules']) > 0:
            label = []
            for specialRule in weapon['specialRules']:
                label.append(str(specialRule['label']))
            pdf.setFont("italic", 10)

            pdf.drawString(startX + offsetX[4], startY + offsetY, ", ".join(label))
        else:
            pdf.drawString(startX + offsetX[4], startY + offsetY, "-")

        offsetY -= 12

    if 'equipment' in unit and len(unit['equipment']) > 0:
        offsetY -= 5

        pdf.setFont("bold", 10)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(startX + offsetX[0], startY + offsetY, "Upgrades")
        offsetY -= 13
        color = 1
        toughness = 0

        for equipment in unit['equipment']:
            pdf.setFont("regular", 10)
            
            if color == 1:
                color = 0.7421875
            else:
                color = 1

            pdf.saveState() 
            pdf.setFillColorRGB(color, color, color)
            pdf.setStrokeColorRGB(color,color,color)
            pdf.rect(startX + offsetX[0],startY + offsetY - 2,290,10, fill=1)
            pdf.restoreState()

            pdf.setFillColorRGB(0, 0, 0)
            pdf.drawString(startX + offsetX[0], startY + offsetY, equipment['name'])
            label = []
            for specialRule in equipment['specialRules']:
                logger.debug("specialRule:")
                logger.debug(specialRule)
                #logger.debug("\n")
                label.append(str(specialRule['label']))
                # if specialRule['name'] == "Tough":
                #     toughness += specialRule['rating']

            
            pdf.setFont("italic", 10)
            pdf.drawString(startX + offsetX[4], startY + offsetY, ", ".join(label))
            offsetY -= 12


def unitOverview(pdf, dataCardParameters, army):
    startX = dataCardParameters['sideClearance'] + 2
    startY = dataCardParameters['pdfSize'][1] - dataCardParameters['topClearance'] - 7
    offsetY = 0
    fontSize = 7

    lines = []
    for unit in army['units']:
        if ('type' not in unit):
            unitInfo = unit['name']
        elif (unit['type'] != unit['name']):
            unitInfo = unit['name'] + " (" + unit['type'] + ")"
        else:
            unitInfo = unit['type']

        unitInfo += " [" + str(unit['size']) + "]"
        unitInfo += " -" + str(getUnitCost(unit)) + " pts"
        lines.append(unitInfo)

    pdf.setFont("bold", fontSize)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawString(startX, startY + offsetY, army['listName'] +
                   " [" + army['armyName'] + "] - " + str(army['listPoints']) + " pts")
    offsetY -= 15

    for line in lines:
        pdf.setFont("regular", fontSize)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(startX, startY + offsetY, line)
        offsetY -= 10
        if startY + offsetY < dataCardParameters['bottomClearance']:
            dataCardBoarderFrame(pdf, dataCardParameters)
            pdf.showPage()
            offsetY = 0

    dataCardBoarderFrame(pdf, dataCardParameters)
    pdf.showPage()

def dataCardSpells(pdf, dataCardParameters, army):
    casterArmyIds = []
    regEx = r'(?i)(Caster|Psychic Host)'
    logger.info(f'Check Spells for units with Spells')
    logger.debug(f'RegEx: {regEx}')
    for unit in army['units']:
        for rule in unit['rules']:
            if re.search(regEx, rule['name']):
                logger.debug(f'Spell unit {unit["name"]} for {rule["name"]}')
                if unit['armyId'] not in casterArmyIds:
                    casterArmyIds.append(unit['armyId'])

    if len(casterArmyIds) == 0:
        return
    
    dataCardBoarderFrame(pdf, dataCardParameters)
    startX = dataCardParameters['sideClearance'] + 2
    startY = dataCardParameters['pdfSize'][1] - dataCardParameters['topClearance'] - 7
    offsetY = 0
    fontSize = 7

    for armyId in casterArmyIds:
        logger.info(f'Get spells from {armyId}')
        armyRules = loadJsonFile(os.path.join(settings['path']['dataFolderArmyBook'], armyId + "_" + str(army['gameSystemId']) + ".json"))
        # Army Name
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("bold", fontSize)
        pdf.drawString(startX, startY + offsetY, armyRules['name'] + " Army Spells")
        offsetY -= (fontSize + 5)

        for spell in armyRules['spells']:
            spellName = f'{spell["name"]} ({spell["threshold"]})'
            effect = getTextWithDiceRoll(spell['effect'], settings['2w6'])
            parts = effect.split(" ")
            offsetXName = pdf.stringWidth(spellName + ": ", "bold", fontSize)

            lines = []
            lineParts = []
            offsetXCalc = offsetXName
            for part in parts:
                if startX + offsetXCalc + pdf.stringWidth(" ".join(lineParts), "regular", fontSize) + pdf.stringWidth(" ".join(part), "regular", fontSize) > dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance']:
                    lines.append(" ".join(lineParts))
                    lineParts = []
                    offsetXCalc = 0
                lineParts.append(part)
            lines.append(" ".join(lineParts))

            if startY - (len(lines)*fontSize) + offsetY < dataCardParameters['bottomClearance']:
                pdf.showPage()
                dataCardBoarderFrame(pdf, dataCardParameters)
                offsetY = 0

            # Name
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("bold", fontSize)
            pdf.drawString(startX, startY + offsetY, spellName + ": ")

            # Description
            pdf.setFont("regular", fontSize)
            pdf.setFillColorRGB(0, 0, 0)
            for line in lines:
                pdf.drawString(startX + offsetXName, startY + offsetY, line)
                offsetY -= fontSize
                offsetXName = 0
            offsetY -= 3
    pdf.showPage()

def dataCardRuleInfo(pdf, dataCardParameters, army):
    rules = []
    seen = set()

    for unit in army['units']:
        for rule in unit['rules']:
            name = rule['name']
            if name not in seen:
                seen.add(name)
                rules.append(name)

    for rule in army.get('specialRules', []):
        name = rule['name']
        if name not in seen:
            seen.add(name)
            rules.append(name)

        for weapon in unit['weapons']:
            for rule in weapon.get('specialRules', []):
                name = rule['name']
                if name not in seen:
                    seen.add(name)
                    rules.append(name)

        for equipment in unit.get('equipment', []):
            for rule in equipment.get('specialRules', []):
                name = rule['name']
                if name not in seen:
                    seen.add(name)
                    rules.append(name)
    rules.sort()
    rules = list(dict.fromkeys(rules))
    ruleDescriptions = []
    downloadCommonRules(army['gameSystemId'])
    commonRules = loadJsonFile(os.path.join(settings['path']['dataFolderArmyBook'], "common-rules_" + str(army['gameSystemId']) + ".json"))
    for rule in rules:
        for common in commonRules['rules']:
            if common['name'].lower() == rule.lower():
                ruleDescriptions.append({'name': common['name'], 'description': common['description']})

    if 'armyIds' in army:
        for armyId in army.get('armyIds', []):
            armyRules = loadJsonFile(os.path.join(
                settings['path']['dataFolderArmyBook'], armyId + "_" + str(army['gameSystemId']) + ".json"))
            # logger.info("START")
            # logger.info(armyRules)
            # logger.info("END")
            for rule in rules:
                #for armyRule in armyRules['specialRules']:
                for armyRule in armyRules.get('specialRules', []):
                    if armyRule['name'].lower() == rule.lower():
                        ruleDescriptions.append({'name': armyRule['name'], 'description': armyRule['description']})

    dataCardBoarderFrame(pdf, dataCardParameters)

    startX = dataCardParameters['sideClearance'] + 2
    startY = dataCardParameters['pdfSize'][1] - dataCardParameters['topClearance'] - 7
    offsetY = 0
    fontSize = 7
    color = 1

    ## Loop units in order they were originally written
    for unit in army['units']:
        unitSeen = set()
        unitRules = []
        for rule in unit['rules']:
            if rule['name'] not in unitSeen:
                unitSeen.add(rule['name'])
        for equipment in unit.get('equipment', []):
            for rule in equipment.get('specialRules', []):
                if rule['name'] not in unitSeen:
                    unitSeen.add(rule['name'])
        #logger.info(unitSeen)

        for rule in unitSeen:
            offsetXName = pdf.stringWidth(rule + ": ", "bold", fontSize)
            rule_desc_list = [r for r in ruleDescriptions if r['name'] == rule]
            if not rule_desc_list:
                logger.warning(f"No description found for rule: {rule}")
                continue

            description = getTextWithDiceRoll(rule_desc_list[0]['description'], settings['2w6'])
            #description = getTextWithDiceRoll([r for r in ruleDescriptions if r['name'] == rule][0]['description'], settings['2w6'])
            parts = description.split(" ")
            lines = []
            lineParts = []
            offsetXCalc = offsetXName
            for part in parts:
                if startX + offsetXCalc + pdf.stringWidth(" ".join(lineParts), "regular", fontSize) + pdf.stringWidth(" ".join(part), "regular", fontSize) > dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance']:
                    lines.append(" ".join(lineParts))
                    lineParts = []
                    offsetXCalc = 0
                lineParts.append(part)
            lines.append(" ".join(lineParts))

            if startY - (len(lines)*fontSize) + offsetY < dataCardParameters['bottomClearance']:
                pdf.showPage()
                dataCardBoarderFrame(pdf, dataCardParameters)
                offsetY = 0

            # Name
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("bold", fontSize)
            pdf.drawString(startX, startY + offsetY, rule + ": ")

            # Description
            pdf.setFont("regular", fontSize)
            pdf.setFillColorRGB(0, 0, 0)
            for line in lines:
                pdf.drawString(startX + offsetXName, startY + offsetY, line)
                offsetY -= fontSize
                offsetXName = 0

            offsetY -= 3
        pdf.showPage()
        dataCardBoarderFrame(pdf, dataCardParameters)
        offsetY = 0
    
    # for rule in ruleDescriptions:

    #     offsetXName = pdf.stringWidth(rule['name'] + ": ", "bold", fontSize)

    #     description = getTextWithDiceRoll(rule['description'], settings['2w6'])
    #     parts = description.split(" ")
    #     lines = []
    #     lineParts = []
    #     offsetXCalc = offsetXName
    #     for part in parts:
    #         if startX + offsetXCalc + pdf.stringWidth(" ".join(lineParts), "regular", fontSize) + pdf.stringWidth(" ".join(part), "regular", fontSize) > dataCardParameters['pdfSize'][0] - dataCardParameters['sideClearance']:
    #             lines.append(" ".join(lineParts))
    #             lineParts = []
    #             offsetXCalc = 0
    #         lineParts.append(part)
    #     lines.append(" ".join(lineParts))

    #     if startY - (len(lines)*fontSize) + offsetY < dataCardParameters['bottomClearance']:
    #         pdf.showPage()
    #         dataCardBoarderFrame(pdf, dataCardParameters)
    #         offsetY = 0

                ##
        #highlight alternating rows
        # if color == 1:
        #    color = 0.7421875
        # else:
        #    color = 1

        # pdf.saveState() 
        # pdf.setFillColorRGB(color, color, color)
        # pdf.setStrokeColorRGB(color,color,color)
        # #Size of this row
        # logger.info(lines)
        # pdf.rect(startX, startY + offsetY,295,len(lines)*15, fill=1)
        # pdf.restoreState() 
        ##

        # Name
    #     pdf.setFillColorRGB(0, 0, 0)
    #     pdf.setFont("bold", fontSize)
    #     pdf.drawString(startX, startY + offsetY, rule['name'] + ": ")

    #     # Description
    #     pdf.setFont("regular", fontSize)
    #     pdf.setFillColorRGB(0, 0, 0)
    #     for line in lines:
    #         pdf.drawString(startX + offsetXName, startY + offsetY, line)
    #         offsetY -= fontSize
    #         offsetXName = 0
    #     offsetY -= 3
    #    pdf.showPage()


def getPdfFileName(armyName):
    pdfName = re.sub(r'(?is)([^\w])', '_', armyName.lower())
    pdfName = re.sub(r'(?is)(_+)', '_', pdfName)
    pdfFile = os.path.join(settings['path']['dataCardFolder'], pdfName)

    if os.path.exists(pdfFile + ".pdf"):
        nr = 1
        while (os.path.exists(pdfFile + "_" + str(nr) + ".pdf")):
            nr += 1
        pdfFile = pdfFile + "_" + str(nr)
    return pdfFile + ".pdf"


def createDataCard(army):
    if settings['2w6']:
        logger.info(f'Create datacards with 2x W6')
    else:
        logger.info(f'Create datacards')

    try:
        pdfmetrics.registerFont(TTFont('bold', os.path.join(
            settings['path']['fontFolder'], "rosa-sans", "hinted-RosaSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont('regular', os.path.join(
            settings['path']['fontFolder'], "rosa-sans", "hinted-RosaSans-Regular.ttf")))
        pdfmetrics.registerFont(TTFont('italic', os.path.join(
            settings['path']['fontFolder'], "rosa-sans", "hinted-RosaSans-Italic.ttf")))
    except Exception as ex:
        logger.error("Font is missing!")
        logger.error(ex)
        return False

    dataCardParameters = {
        'pdfSize': (300.0, 200.0),
        'lineColor': [1.00, 0.55, 0.10],
        'topClearance': 10,
        'bottomClearance': 10,
        'sideClearance': 2,
    }

    # creating a pdf object
    pdfFile = getPdfFileName(army['listName'])
    pdf = canvas.Canvas(pdfFile, pagesize=dataCardParameters['pdfSize'])
    pdf.setTitle("GDF data card")

    image_infos = get_image_infos(settings)
    for unit in army['units']:
        #logger.info(f'{unit["name"]} ({unit["id"]})')
        #unit['size']
        #logger.info(unit)
        dataCardBoarderFrame(pdf, dataCardParameters)
        dataCardUnitType(pdf, dataCardParameters, unit)
        dataCardUnitWounds(pdf, dataCardParameters, unit, army)
        dataCardUnitRules(pdf, dataCardParameters, unit)
        dataCardUnitPoints(pdf, dataCardParameters, unit)
        dataCardUnitImage(pdf, dataCardParameters, unit, army['listName'], army['armyName'], image_infos)
        dataCardUnitName(pdf, dataCardParameters, unit)
        dataCardUnitSkills(pdf, dataCardParameters, unit)
        dataCardUnitWeaponsEquipment(pdf, dataCardParameters, unit)
        if 'armyVersions' in army:
           dataCardArmyBookVersion(pdf, dataCardParameters, army['armyVersions'], unit['armyId'])

        pdf.showPage()
    dataCardRuleInfo(pdf, dataCardParameters, army)
    dataCardSpells(pdf, dataCardParameters, army)

    unitOverview(pdf, dataCardParameters, army)

    try:
        pdf.save()
        logger.info("Datacards finished ...")
        return pdfFile
    except Exception as ex:
        logger.error("Error PDF save failed")
        logger.error(str(ex))
        return None

def get_image_infos(settings):
    image_infos = loadJsonFile(settings['path']['imageJson'])

    # Convert old image to images list
    for rule in image_infos:
        if 'image' in rule and type(rule['image']) == str:
            rule['images'] = [rule['image']]
            del rule['image']

        if 'images' in rule and type(rule['images']) == str:
            rule['images'] = [rule['images']]
        
        if 'image' in rule and type(rule['image']) == list:
            rule['images'] = rule['image']
            del rule['image']

    # Add used counter
    for rule in image_infos:
        unit_images = []
        for image in rule['images']:
            unit_images.append({'file': image, 'used': 0})
        rule['images'] = unit_images

    return image_infos

def getTxtSpecialRule(txt):
    rule = {}
    rule['label'] = txt

    if "(" in txt:
        data = txt.split("(")
        rule['key'] = data[0].lower()
        rule['name'] = data[0]
        rule['rating'] = re.sub(r'(?is)([^\d])', '', data[1])
    else:
        rule['key'] = txt.lower()
        rule['name'] = txt
    return rule


def getRulesFromTxt(data):
    parts = list(data.strip(" "))
    rules = []
    extract = []
    bracket = 0
    for i in range(len(parts)):
        if (parts[i] == "("):
            bracket += 1
        elif (parts[i] == ")"):
            bracket -= 1
        if ((parts[i] == "," and bracket == 0) or i == len(parts) - 1):
            if i == len(parts) - 1:
                extract.append(parts[i])
            rules.append(''.join(extract).strip())
            extract = []
        else:
            extract.append(parts[i])

    return rules


def parseArmyTextList(armyListText):
    armyData = {}

    length = len(armyListText[0])
    if (length > 6 and armyListText[0][0] == "+" and armyListText[0][1] == "+" and armyListText[0][2] == " " and armyListText[0][length - 3] == " " and armyListText[0][length - 2] == "+" and armyListText[0][length - 1] == "+"):
        armyData['parser'] = "txt"

        data = armyListText[0].rstrip(" ++").lstrip("++ ").split("[")
        tmp = data[0].strip().split("-")
        armyData['armyName'] = tmp[len(tmp) - 1].strip()
        tmp.pop(len(tmp) - 1)
        armyData['listName'] = "-".join(tmp).strip()

        data = data[1].split(" ")
        armyData['gameSystem'] = data[0].lower()
        armyData['gameSystemId'] = getGameSystemId(armyData['gameSystem'])
        armyData['listPoints'] = int(re.sub(r'(?is)([^\d])', '', data[1]))
    else:
        logger.error("Error no valid army data found!")
        return False

    unit = False
    armyData['units'] = []
    unitData = {}
    for x in range(1, len(armyListText)):
        if len(armyListText[x]) > 5:
            if unit == False and armyListText[x].count('|') == 2:
                unitData = {}
                unit = True
                data = armyListText[x].split("|")
                unitData['cost'] = re.sub(r'[^\d]', '', data[1].strip(" "), )
                unitData['rules'] = []
                unitData['equipment'] = []
                unitData['id'] = f'{x}'
                rules = getRulesFromTxt(data[2])
                for rule in rules:
                    if re.search(r'(?is)\([A-Z]+', rule.strip()):
                        regExMatch = re.search(r"(?is)(\dx)?([^(]+)(\()(.*)(\))", rule.strip(" "))
                        equipment = {}
                        equipment['name'] = regExMatch.group(2).strip()
                        equipment['specialRules'] = []
                        for equipmentRule in regExMatch.group(4).split(","):
                            equipment['specialRules'].append(getTxtSpecialRule(equipmentRule))
                        unitData['equipment'].append(equipment)
                    else:
                        unitData['rules'].append(getTxtSpecialRule(rule))
                regExMatch = re.findall(
                    r"(?P<name>.*)\s\[(?P<unitCount>\d+)\]\sQ(?P<quality>\d+)\+\sD(?P<defense>\d+)\+\sC(?P<combined>\d+)\+\sJ(?P<joinToUnit>\d+)\+\sS(?P<selectionId>\d+)\+$", data[0].strip(" "))
                unitData['name'] = regExMatch[0][0]
                unitData['type'] = ""
                unitData['size'] = int(regExMatch[0][1])
                unitData['quality'] = int(regExMatch[0][2])
                unitData['combined'] = bool(regExMatch[0][3])
                unitData['joinToUnit'] = regExMatch[0][4]
                unitData['selectionId'] = regExMatch[0][5]

            elif unit == True:
                weapons = getRulesFromTxt(armyListText[x].strip(" "))

                for weapon in weapons:
                    regExMatch = re.search(
                        r"(\d+x)?([^(]+)(\()(.*)(\))", weapon.strip(" "))
                    weaponData = {}
                    weaponData['name'] = regExMatch.group(2).strip()
                    weaponData['count'] = regExMatch.group(1)
                    if weaponData['count'] == None:
                        weaponData['count'] = 1
                    else:
                        weaponData['count'] = int(weaponData['count'].replace("x", ""))

                    weaponRules = regExMatch.group(4).split(",")
                    for weaponRule in weaponRules:
                        weaponRule = weaponRule.strip(" ")
                        if re.match(r'\d+"', weaponRule):
                            weaponData['range'] = int(
                                weaponRule.replace('"', ''))
                        elif re.match(r'A\d+', weaponRule):
                            weaponData['attacks'] = int(
                                weaponRule.replace("A", ""))
                        elif re.match(r'AP\(\d+\)', weaponRule):
                            weaponData['ap'] = int(weaponRule.replace(
                                "AP(", "").replace(")", ""))
                        else:
                            if not "specialRules" in weaponData:
                                weaponData['specialRules'] = []
                            weaponData['specialRules'].append(getTxtSpecialRule(weaponRule))
                    if not "weapons" in unitData:
                        unitData['weapons'] = []
                    unitData['weapons'].append(weaponData)
        else:
            unit = False
            if "name" in unitData:
                armyData['units'].append(unitData)
            unitData = {}
    return armyData


def getUnit(unit, jsonArmyBookList):
    logger.debug(f'{unit["id"]} from {unit["armyId"]}')
    data = {}
    for listUnit in jsonArmyBookList[unit['armyId']]['units']:
        if (listUnit['id'] == unit['id']):
            data['type'] = listUnit['name']
            data['name'] = listUnit['name']
            #logger.info(f'{data["type"]} / {data["name"]} ({unit["id"]})')
            data['armyId'] = unit['armyId']
            data['id'] = listUnit['id']
            data['cost'] = listUnit['cost']
            data['defense'] = listUnit['defense']
            data['quality'] = listUnit['quality']
            data['upgrades'] = listUnit['upgrades']
            data['size'] = listUnit['size']
            data['selectionId'] = unit['selectionId']
            #data['combined'] = unit['combined']

            if "combined" in unit:
                data['combined'] = unit['combined']
            else:
                data['combined'] = False

            if "joinToUnit" in unit:
                data['joinToUnit'] = unit['joinToUnit']
            else:
                data['joinToUnit'] = None
            
            if "notes" in unit:
                data['notes'] = unit['notes']
            else:
                data['notes'] = None
            data['weapons'] = []

            for weapon in listUnit['weapons']:
                data['weapons'].append(getWeapon(weapon))
            
            items = getItems(listUnit['items'])
            if 'equipment' not in data:
                data['equipment'] = []
            data['equipment'] += items

            data['rules'] = getRules(listUnit['rules'])
            data = getUnitUpgrades(unit, data, jsonArmyBookList)
            break
    if "customName" in unit:
        data['name'] = unit['customName']

    return data


def getItems(data):
    logger.debug(f'{len(data)}x') 

    items = []
    for item in data:
        rules = getRules(item['content'])
        items.append({
            'name': item['name'],
            'specialRules': rules
        })

    return items

def getRules(data):
    logger.debug(f'{len(data)}x') 
    rules = []
    for specialRule in data:
        logger.debug(f'{specialRule["name"]}') 

        rule = specialRule
        if 'rating' in specialRule and specialRule['rating'] != '':
            rule['label'] = specialRule['name'] + \
                "(" + str(specialRule['rating']) + ")"
        else:
            rule['label'] = specialRule['name']

        rules.append(rule)

    return rules


def getWeapon(data, modCount=-1):
    logger.debug(f'{data["name"]}') 

    weapon = {}
    weapon['attacks'] = data['attacks']

    if (modCount != -1):
        weapon['count'] = modCount
    else:
        weapon['count'] = data['count']

    if "name" in data:
        weapon['name'] = data['name']

    if "range" in data and data['range'] > 0:
        weapon['range'] = data['range']

    weapon['specialRules'] = getRules(data['specialRules'])

    for i in range(len(weapon['specialRules'])):
        if weapon['specialRules'][i]['name'].lower() == "ap":
            weapon['ap'] = weapon['specialRules'][i]['rating']
            weapon['specialRules'].pop(i)
            break

    return weapon

def removeItem(removeItems: list, count: int, originalItems: dict, type=""):
    logger.debug(f'{removeItems} from {type}')
    logger.debug(f'{removeItems} from {originalItems}')
    for remove in removeItems:
        for i in range(len(originalItems)):
            remove = remove.strip()
            group = [remove, remove + "s", remove[:-1]]
            if re.match(r'^(' + "|".join(group) + ')$', originalItems[i]['name'].strip()):
                if ('count' not in originalItems[i] or count == "any" or count == None or originalItems[i]['count'] == 1):
                    logger.debug("if")
                    originalItems.pop(i)
                else:
                    logger.debug("else")
                    originalItems[i]['count'] = int(originalItems[i]['count']) - count
                    #originalItems[i]['count'] -= count
                    if originalItems[i]['count'] <= 0:
                        originalItems.pop(i)
                break
    return originalItems


def getUnitUpgrades(unit, unitData, jsonArmyBookList):
    logger.debug(f'{len(unit["selectedUpgrades"])}x') 
    for upgrade in unit['selectedUpgrades']:
        armyId = unit['armyId']
        upgradeId = upgrade['upgradeId']
        optionId = upgrade['optionId']
        unitId = unit['id']

        logger.debug(f'upgradeId: {upgradeId} optionId: {optionId}') 

        for package in jsonArmyBookList[armyId]['upgradePackages']:
            for section in package['sections']:
                variant = None
                affects = None
                targets = None
                if "variant" in section:
                    variant = section['variant']
                if "affects" in section:
                    affects = section['affects']
                if "targets" in section:
                    targets = section['targets']

                if (section['uid'] == upgradeId):
                    for option in section['options']:
                        if option['uid'] == optionId:

                            if ('upgradeCost' not in unitData):
                                unitData['upgradeCost'] = []
                            
                            cost = 0
                            # Regular cost
                            if 'cost' in option:
                                cost = option['cost']
                            
                            # Cost for unit
                            if 'costs' in option:
                                for costs4unit in option['costs']:
                                    if costs4unit['unitId'] == unitId:
                                        logger.debug("Use unit cost")
                                        cost = costs4unit['cost']
                            
                            if cost != 0:
                                unitData['upgradeCost'].append(cost)

                            for gains in option['gains']:
                                logger.debug(f'Type: {gains["type"]}')
                                if (gains['type'] == "ArmyBookWeapon"):
                                    if variant in ("upgrade", "replace") and affects and affects['type'] == "all":
                                        modeCount = unitData['size']
                                    else:
                                        modeCount = -1
                                    unitData['weapons'].append(getWeapon(gains, modeCount))
                                elif gains['type'] == "ArmyBookItem":
                                    rule =  getRules(gains['content'])
                                    if 'equipment' not in unitData:
                                        unitData['equipment'] = []
                                    unitData['equipment'].append(addEquipment(gains, True))

                                    if 'rules' not in unitData:
                                        unitData['rules'] = []
                                    unitData['rules'] += rule
                                elif gains['type'] == "ArmyBookRule":
                                    unitData['rules'].append(getRules([gains])[0])
                                else:
                                    logger.error("Error no handling for " +
                                          gains['type'] + " upgradeId " + upgradeId + " optionId " + optionId)

                            if variant == "replace":
                                if (gains['type'] == "ArmyBookWeapon" or gains['type'] == "ArmyBookItem"):
                                    if affects and affects['type'] == "any":
                                        # Not sure, but by Desolator Squad HE-Launchers missing during upgrade uNapO (Replace any HE-Launcher), workarround set affects to 1
                                        affectsValue = 1
                                    elif affects and affects['type'] == "exactly":
                                        affectsValue = affects['value']
                                    elif affects and affects['type'] == "all":
                                        affectsValue = None
                                    elif affects and affects['type'] == "up to":
                                        affectsValue = affects['value']
                                    elif affects is None:
                                        affectsValue = 999
                                    else:
                                        logger.warning("Default handling for " + str(affects))
                                        affectsValue = 1

                                    if unitData['size'] > 1:
                                        unitData['weapons'] = mergeWeapon(unitData['weapons'])

                                    unitData['weapons'] = removeItem(targets, affectsValue, unitData['weapons'], 'weapons')
                                    if 'equipment' in unitData:
                                        unitData['equipment'] = removeItem(targets, affectsValue, unitData['equipment'], 'equipment')
                                else:
                                    logger.error(f"Unhandelt type '{gains['type']}' in unit upgrades")

    return unitData


def mergeWeapon(weapons):
    logger.debug('Start')

    mergedWeapons = []
    for weapon in weapons:
        add = True
        for added in mergedWeapons:
            if added['name'] == weapon['name'] and added['attacks'] == weapon['attacks']:
                if 'ap' not in added or 'ap' in added and added['ap'] == weapon['ap']:
                    added['count'] += weapon['count']
                    add = False
                    break

        if (add == True):
            mergedWeapons.append(weapon)
    return mergedWeapons


def addEquipment(data, specialRules = True):
    logger.debug(f'Add {data["name"]}')
    equipment = {}
    equipment['name'] = data['name']
    if specialRules == True:
        equipment['specialRules'] = getRules(data['content'])
    else:
        equipment['specialRules'] = []

    return equipment


def parseArmyJsonList(armyListJsonFile: str, validateVersion=True):
    logger.info("Parse army list ...")
    armyData = {}
    jsonArmyBookList = {}

    jsonArmyList = loadJsonFile(armyListJsonFile)
    if 'list' not in jsonArmyList or 'name' not in jsonArmyList['list']:
        logger.error(f'Invalid json file ')
        return

    armyData['armyId'] = jsonArmyList['armyId']
    armyData['gameSystem'] = jsonArmyList['gameSystem']
    armyData['gameSystemId'] = getGameSystemId(jsonArmyList['gameSystem'])
    armyData['armyVersions'] = jsonArmyList['armyVersions']
    armyData['armyIds'] = jsonArmyList['armyIds']

    for armyId in jsonArmyList['armyIds']:
        downloadArmyBook(armyId, armyData['gameSystemId'])
        jsonArmyBookList[armyId] = loadJsonFile(os.path.join(
            settings['path']['dataFolderArmyBook'], armyId + "_" + str(armyData['gameSystemId']) + ".json"))
    downloadCommonRules(armyData['gameSystemId'])

    for armyVersion in jsonArmyList['armyVersions']:
        versionCheck = checkArmyVersions(jsonArmyList, jsonArmyBookList, armyVersion['armyId'])
        if (validateVersion and not versionCheck):
            armyVersionsDifference()
    armyData['armyName'] = jsonArmyBookList[armyData['armyId']]['name']
    armyData['listPoints'] = jsonArmyList['listPoints']
    armyData['listName'] = jsonArmyList['list']['name']

    armyData['units'] = []
    for unit in jsonArmyList['list']['units']:
        unitData = getUnit(unit, jsonArmyBookList)
        if unitData != {}:
            if unitData['combined'] and unit['joinToUnit'] is not None:
                target_unit = next((u for u in armyData['units'] if u['selectionId'] == unit['joinToUnit']), None)
                if target_unit:
                    logger.debug(f"Combining unit '{unitData['name']}' with '{target_unit['name']}'")
                    target_unit['size'] += unitData['size']
                    for weapon in unitData['weapons']:
                        match = next((w for w in target_unit['weapons'] if w['name'] == weapon['name'] and w.get('ap') == weapon.get('ap')), None)
                        if match:
                            match['count'] += weapon['count']
                        else:
                            target_unit['weapons'].append(weapon)
                else:
                    logger.warning(f"joinToUnit '{unit['joinToUnit']}' not found. Adding unit as standalone.")
                    armyData['units'].append(unitData)
            elif unitData['combined'] and unit['joinToUnit'] is None:
                logger.info("Combined with No JoinTo")
                armyData['units'].append(unitData)
            else:
                armyData['units'].append(unitData)
    #logger.info(armyData)
    return armyData

def armyVersionsDifference():
    logger.warning("Army Book version from JSON is different than Army Book Version from OPR Server")
    waitForKeyPressAndExit()

def loadJsonFile(jsonFile: str):
    try:
        f = open(jsonFile, encoding="utf8")
        file = f.read()
        f.close()
    except Exception as ex:
        logger.error("file failed to open " + jsonFile)
        logger.error(ex)
        return False

    try:
        jsonObj = json.loads(file)
    except json.decoder.JSONDecodeError as ex:
        logger.error(file + " Json is not valid!")
        logger.error(ex)
        return False
    except Exception as ex:
        logger.error("Unhandeld Exception")
        logger.error(ex)
        return False
    return jsonObj


def getGameSystemId(gameSystem: str):
    if (gameSystem == "gf"):
        return 2
    elif (gameSystem == "gff"):
        return 3
    elif (gameSystem == "aof"):
        return 4
    elif (gameSystem == "aofs"):
        return 5
    elif (gameSystem == "aofr"):
        return 6
    else:
        return 0


def downloadArmyBook(id: str, gameSystemId):
    logger.debug(f'Check/download army book {id}/{gameSystemId}')
    armyBookJsonFile = os.path.join(settings['path']['dataFolderArmyBook'], str(id) + "_" + str(gameSystemId) + ".json")
    url = f'https://army-forge.onepagerules.com/api/army-books/{id}?gameSystem={gameSystemId}'

    return downloadJson(url, armyBookJsonFile)


def downloadCommonRules(gameSystemId):
    logger.debug(f'Check/download common rules game system {gameSystemId}')
    armyBookJsonFile = os.path.join(settings['path']['dataFolderArmyBook'], "common-rules_" + str(gameSystemId) + ".json")
    url = f'https://army-forge.onepagerules.com/api/rules/common/{gameSystemId}'
    return downloadJson(url, armyBookJsonFile)


def downloadJson(url, file):
    # download only when older than 1 day
    download = True
    if os.path.exists(file):
        if time.time() - os.stat(file)[stat.ST_MTIME] < 86400:
            download = False

    if (download == True):
        try:
            logger.debug("Download file")
            urllib.request.urlretrieve(url, file)
        except Exception as ex:
            logger.error(f'Error for {url}')
            logger.error(ex)
            return False

    if not os.path.exists(file):
        logger.error("No json data found " + id)
        return False

    return True


def saveDictToJson(dictData, file):
    try:
        with open(file, 'w') as fp:
            fp.write(json.dumps(dictData, indent=4))
    except Exception as ex:
        logger.error("Error saving dict to json")
        logger.error(ex)
        return False
    return True


def checkFonts():
    logging.debug("Start")
    font1 = os.path.join(settings['path']['fontFolder'], "rosa-sans", "hinted-RosaSans-Bold.ttf")
    font2 = os.path.join(settings['path']['fontFolder'], "rosa-sans", "hinted-RosaSans-Regular.ttf")

    if not os.path.exists(font1) or not os.path.exists(font2):
        logger.debug("Download font ...")

        url = "https://raw.githubusercontent.com/JackGruber/OPRDataCards/master/rosa-sans.zip"
        zipFile = os.path.join(settings['path']['fontFolder'], "rosa-sans.zip")
        if downloadFile(url, zipFile) == True:
            logger.debug("Unzip fonts ...")
            with zipfile.ZipFile(zipFile, 'r') as zipRef:
                zipRef.extractall(os.path.join(settings['path']['fontFolder'], "rosa-sans"))


def downloadFile(url, dstFile):
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(dstFile, "wb") as file:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            return True
        else:
            logger.error("Error font download failed")
            return False
    except Exception as ex:
        logger.error("Error font download failed")
        logger.error(ex)
        return False

def checkArmyVersions(armyJson, armyBookJson, armyId):
    logger.debug(f'armyId {armyId}')

    # Get Army Version
    armyVersion = None
    for armyVersion in armyJson["armyVersions"]:
        if armyVersion['armyId'] == armyId:
            armyVersion = armyVersion['version']
            break

    try:
        bookVersion = armyBookJson[armyId]["versionString"]
    except Exception as ex:
        logger.error("Error on checkArmyVersions")
        logger.error(ex)
        return False
    
    logger.debug(f'{armyVersion} / {bookVersion}')
    if str(armyVersion) == str(bookVersion):
        return True
    else:
        logger.error(f"Army version {armyVersion} don't match ArmyBook version {bookVersion}")
        return False

def waitForKeyPressAndExit():
    input("Press Enter to continue...")
    sys.exit(1)

def getDiceRoll(w6: int, as2w6: False):
    if as2w6:
        if w6 == 6:
            #return '6/9'
            return '10'
        #return f'{w6}/{w6 + 3}'
        return f'{w6 + 3}'
    else:
        return f'{w6}'

def getTextWithDiceRoll(text, as2w6: False):
    if not as2w6:
        return text

    # Replace 6 with +
    text = re.sub(r'6(?!\stoken)', getDiceRoll(6, True) + "+", text)
    text = re.sub(r'5\+', getDiceRoll(5, True) + "+", text)
    text = re.sub(r'4\+', getDiceRoll(4, True) + "+", text)
    text = re.sub(r'3\+', getDiceRoll(3, True) + "+", text)
    text = re.sub(r'2\+', getDiceRoll(2, True) + "+", text)
    text = re.sub(r'1\+', getDiceRoll(1, True) + "+", text)

    return text
def gui_geometry(tkRoot, window_width, window_height):
    # Bildschirmbreite und -höhe abrufen
    screen_width = tkRoot.winfo_screenwidth()
    screen_height = tkRoot.winfo_screenheight()
    
    # Berechnen, um das Fenster zu zentrieren
    position_x = (screen_width - window_width) // 2
    position_y = (screen_height - window_height) // 2

    tkRoot.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
    tkRoot.resizable(False, False)

def gui_create():
    # Hauptfenster erstellen
    root = tk.Tk()
    root.title("GDFDataCards")
    gui_geometry(root, 600, 300)
    root.configure(bg="#f0f0f0")

    # Stil anpassen
    style = ttk.Style(root)
    style.theme_use("clam")  # Verwenden eines modernen Themes
    style.configure("TButton", font=("Helvetica", 10), padding=5)
    style.configure("TFrame", background="#f0f0f0")
    style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 12))
    style.configure("TCheckbutton", background="#f0f0f0", borderwidth=0)

    # Haupt-Frame erstellen
    frame = ttk.Frame(root, padding=(10, 10))
    frame.pack(fill="both", expand=True)

    # Buttons
    button_frame = ttk.Frame(frame)
    button_frame.pack(pady=10)

    process_button = ttk.Button(button_frame, text="Create PDF from OPR ArmyForge file", command=select_file)
    process_button.grid(row=0, column=1, padx=5)

    open_images_button = ttk.Button(button_frame, text="Open images.json", command=open_images_json)
    open_images_button.grid(row=0, column=2, padx=5)

    open_folder_button = ttk.Button(button_frame, text="Open Images Folder", command=open_images_folder)
    open_folder_button.grid(row=0, column=3, padx=5)

    # Checkboxen
    checkbox_frame = ttk.Frame(frame)
    checkbox_frame.pack(pady=(15, 0))

    global debug_var
    debug_var = tk.BooleanVar()
    debug_checkbox = ttk.Checkbutton(checkbox_frame, text="Debug", variable=debug_var, command=toggle_debug)
    debug_checkbox.grid(row=0, column=0, padx=5, pady=5)

    # Log box
    status_frame = ttk.Frame(frame)
    status_frame.pack(fill="both", expand=True)

    global status_box
    status_box = tk.Text(status_frame, wrap="word", height=8, width=45, bg="#e6e6e6", font=("Helvetica", 10))
    status_box.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=status_box.yview)
    scrollbar.pack(side="right", fill="y")

    status_box.config(yscrollcommand=scrollbar.set)

    return root

def toggle_debug():
    status = "aktiviert" if debug_var.get() else "deaktiviert"
    log_status(f'Debug-Modus {status}')
    settings['debug'] = debug_var.get()
    if settings['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

def log_status(message):
    if settings is not None and settings['gui']:
        status_box.insert(tk.END, message + "\n")
        status_box.see(tk.END)  # Scrollt zum Ende der Textbox

def select_file():
    file_path = filedialog.askopenfilename(
        title="Select an OPR ArmyBook file for processing",
        filetypes=[("JSON File", "*.json"), ("TXT File", "*.txt")]
    )
    if file_path:
        log_status("")
        log_status("")
        log_status(f"Start processing the file '{os.path.basename(file_path)}' ...")
        threading.Thread(target=processArmyFile, args=(file_path,), daemon=True).start()

def open_images_json():
    file_path = settings['path']['imageJson']
    if os.path.exists(file_path):
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
            log_status(f"The file '{file_path}' was opened in the default editor.")  # Status in die Statusbox ausgeben
        except Exception as e:
            log_status(f"Error opening the file '{file_path}': {e}")

def open_images_folder():
    folder_path = settings['path']['imageFolder']
    if os.path.isdir(folder_path):
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
            log_status(f"The folder '{folder_path}' was opened in the file explorer.")  # Status in die Statusbox ausgeben
        except Exception as e:
            log_status(f"Error when opening the folder '{folder_path}': {e}")

if __name__ == "__main__":
    Main()    
