import sublime, sublime_plugin
import re
from xml.dom.minidom import Document
import os

class BuildProjectTreeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        #get absolute file name
        fileName = ''
        try:
            fileName = str(self.view.file_name())
            if(fileName == None or fileName == 'None'):
                raise FileNotSavedError
        except FileNotSavedError as e:
            e.display()
        else:
            # get lines from buffer
            lines = self._getLines()

            #extract project path
            path = re.sub(r'\\\w+[.\w+]*$', '', fileName)

            #instanciate Structure
            structure = Structure(lines, path)

            try:
                structure.designStructure()
                structure.buildStructure()
            except (StructureError, FileCreateError, FileWriteError) as e:
                e.display()

            #back to project root
            os.chdir(path)

    def _getBufferRegion(self):
        """
        Get entire buffer region
        """

        endpoint = self.view.size()
        return sublime.Region(0,endpoint)

    def _getLineSet(self):
        """
        Get list of each line region
        """

        bufferRegion = self._getBufferRegion()
        return self.view.split_by_newlines(bufferRegion)

    def _getLines(self):
        """
        Get list of lines as string
        """

        lines = []
        lineSet = self._getLineSet()
        for line in lineSet:
            lines.append(str(self.view.substr(line)))
        return lines

class Structure:
    """
    Has methods for building DOM version of project tree and
    creating files and folders accordingly
    """

    def __init__(self, lines, path):
        #initialize variables
        #lines from buffer
        self._lines = lines
        #path to the project root directory
        self._path = path
        #instantiate ProjectTree so that we can create files and directories inside project directory
        self._tree = ProjectTree(self._path)

        #create document and add empty structure in it
        self._doc = Document()
        self._structure = self._doc.createElement('structure')
        self._doc.appendChild(self._structure)

    def designStructure(self):
        """
        Create DOM version of project tree
        """
        #regex for
        #file
        reFile = re.compile(r'^[\t\s]*([a-z.][.\w]+)\.?(\w+)?\s*$')
        #class
        reClass = re.compile(r'^[\t\s]*([A-Z]\w+)\s*:?(\s*\w+,?)*$')
        #folder
        reFolder = re.compile(r'^[\t\s]*(\w+)/\s*$')
        #attribute
        reProperty = re.compile(r'^[\t\s]*([\+\-#])\s*(\w+)\s*(\w+)\s*$')
        #methods
        reMethod =  re.compile(r'^[\t\s]*([\+\-#])\s*(\w+)\s*(\w+)\s*\((.*)\)$')


        for line in self._lines:
            if(reFile.search(line)):
                self._addNode('file',reFile.search(line))
            elif(reClass.search(line)):
                self._addNode('class',reClass.search(line))
            elif(reFolder.search(line)):
                self._addNode('folder',reFolder.search(line))
            elif(reProperty.search(line)):
                self._addNode('property',reProperty.search(line))
            elif(reMethod.search(line)):
                self._addNode('method',reMethod.search(line))

    def buildStructure(self):
        """
        Build project tree
        """
        #pass structure node of DOM for processing
        self._processNode(self._structure)

    def _processNode(self, node):
        """
        Walk through each nodes
        """
        nodes = node.childNodes
        for node in nodes:
            self._buildNode(node)
            self._processNode(node)

    def _buildNode(self, node):
        nodeType = node.getAttribute('type')
        if(nodeType == 'file'):
            self._tree.makeFile(node)
        elif(nodeType == 'folder'):
            self._tree.makeDir(node)
        elif(nodeType == 'class'):
            self._tree.writeInFile('class', node)
        elif(nodeType == 'method'):
            self._tree.writeInFile('method', node)
        elif(nodeType == 'property'):
            self._tree.writeInFile('property', node)

    def _addNode(self, type, list):
        #get list of tabs
        # print(list.groups())
        tabs = re.findall(r'(\t)',list.group())
        currentLevel = len(tabs)
        currentNode = self._structure

        # path = '.'
        # print('for ' + list.group() + ' level:' + str(currentLevel))
        # print('parentNode:' + currentNode.nodeName)
        for level in range(currentLevel):
            tempNode = currentNode.lastChild
            # print('parentNode:' + tempNode.nodeName)
            if(tempNode):
                # path += '\t.'
                currentNode = tempNode
            else:
                newNode = self._createNode(type, list)
                self._checkNewStructure(currentNode, newNode)
                currentNode.appendChild(newNode)
                # print(path)
                break
        else:
            newNode = self._createNode(type, list)
            self._checkNewStructure(currentNode, newNode)
            currentNode.appendChild(newNode)

    def _createNode(self, type, list):

        node = None

        if(type == 'folder'):
            node = self._doc.createElement(list.group(1))
            node.setAttribute('type', 'folder')

        elif(type == 'file'):
            node = self._doc.createElement(list.group(1))
            node.setAttribute('type', 'file')
            node.setAttribute('extension', list.group(2))

        elif(type == 'class'):
            node = self._doc.createElement(list.group(1))
            node.setAttribute('type', 'class')
            node.setAttribute('inherit', list.group(2))

        elif(type == 'method'):
            node = self._doc.createElement(list.group(3))
            node.setAttribute('type', 'method')
            node.setAttribute('return_type', list.group(2))
            node.setAttribute('arguments', list.group(4))
            scope = ''
            if(list.group(1) == '+'):
                scope = 'public'
            elif(list.group(1) == '-'):
                scope = 'private'
            elif(list.group(1) == '#'):
                scope = 'protected'
            node.setAttribute('scope', scope)

        elif(type == 'property'):
            node = self._doc.createElement(list.group(3))
            node.setAttribute('type', 'property')
            node.setAttribute('data_type', list.group(2))
            scope = ''
            if(list.group(1) == '+'):
                scope = 'public'
            elif(list.group(1) == '-'):
                scope = 'private'
            elif(list.group(1) == '#'):
                scope = 'protected'
            node.setAttribute('scope', scope)
        return node

    def _checkNewStructure(self, parentNode, childNode):
        """
        Check if child node can be inserted inside parent node
        """
        if(childNode.getAttribute('type') == 'folder' or childNode.getAttribute('type') == 'file'):
            #for files and folders if parent node is neither folder nor structure raise error
            if(parentNode.getAttribute('type') != 'folder' and parentNode.nodeName != 'structure'):
                raise StructureError(parentNode, childNode)
        elif(childNode.getAttribute('type') == 'class'):
            #for class if parent node is not file raise error
            if(parentNode.getAttribute('type') != 'file'):
                raise StructureError(parentNode, childNode)
        else:
            #for method and attributes if parent node neither class nor file raise error
            if(parentNode.getAttribute('type') != 'class' and parentNode.getAttribute('type') != 'file'):
                raise StructureError(parentNode, childNode)

class ProjectTree:
    """docstring for ProjectTree"""
    def __init__(self, path):
        self._breadcrumb = []
        self._projectPath = path
        os.chdir(path)

    def makeDir(self, node):
        directory = node.nodeName
        if(node.parentNode.nodeName != self._currentDir()):
            self._getToParent(node.parentNode.nodeName)
        if(self._fileExists(directory) == False):
            try:
                os.mkdir(directory)
            except Exception:
                raise FileCreateError(node)
            os.chdir(directory)
            self._breadcrumb.append(directory)
        else:
            os.chdir(directory)
            self._breadcrumb.append(directory)
        # print(self._breadcrumb)

    def _currentDir(self):
        """
        Return current directory from breadcrumb
        """
        if(len(self._breadcrumb) != 0):
            return self._breadcrumb[len(self._breadcrumb) -1]
        else:
            return None

    def _getToParent(self, directoryName):
        if(directoryName == 'structure'):
            os.chdir(self._projectPath)
            self._breadcrumb = []
        else:
            os.chdir('..')
            self._breadcrumb.pop()
            if(self._currentDir() != directoryName):
                self._getToParent(directoryName)

    def makeFile(self, node):
        fileExtension = node.getAttribute('extension')
        fileName = ''
        if(fileExtension):
            fileName = node.nodeName + '.' + node.getAttribute('extension')
        else:
            fileName = node.nodeName

        if(node.parentNode.nodeName != self._currentDir()):
            self._getToParent(node.parentNode.nodeName)
        if(self._fileExists(fileName) == False):
            try:
                f = open(fileName, 'w')
                f.close()
            except Exception:
                raise FileCreateError(node)
        # print(self._breadcrumb)


    def writeInFile(self, type, node):
        """
        call language specific file
        """
        pass

    def _fileExists(self, file):
        files = os.listdir(os.getcwd())
        fileExists = file in files
        if(fileExists):
            return True
        else:
            return False

class Error(Exception):
    """
    Base class for errors.
    Provides a method for displaying errors.
    """

    def __init__(self, error):
        self.msg = error

    def display(self):
        sublime.error_message(self.msg)

class FileNotSavedError(Error):
    """
    This error is raised when user tries to build structure without saving the structure file.
    """

    def __init__(self):
        Error.__init__(self, 'Could not locate the project structure file.\nPlease save file into the project directory.')

class StructureError(Error):
    """
    This error is raised when parent node has improper child nodes.
    Like folder inside file.
    """

    def __init__(self, parentNode, childNode):
        parentNodeType = parentNode.getAttribute('type')
        parentNodeName = parentNode.nodeName

        childNodeType = childNode.getAttribute('type')
        childNodeName = childNode.nodeName

        Error.__init__(self, 'Illegal structure.\nCannot insert ' + childNodeType + ', ' + childNodeName + ' inside ' + parentNodeType + ', ' + parentNodeName + '.')

class FileCreateError(Error):
    """
    Plugin raises this error when it cannot create file or directory.
    """

    def __init__(self, node):
        (nodeType, nodeName) = (node.getAttribute('type'), node.nodename)
        Error.__init__(self, nodeType + ',' + nodeName + ' could not be created. Make sure you have proper permission.')

class FileWriteError(Error):
    """
    This error raises if file is not writable.
    argList = [(nodeType, nodeName), fileName]
    """

    def __init__(self, argList):
        Error.__init__(self, 'Could not write into file.')
