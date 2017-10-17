'''
In this program we will fix the citations to latex format! 

First all the .tex files in the current directories (and sub-directories) are searched. They are copied into a backup folder that is provided to this program. The program reads every file from the backup folder and writes the modified lines into the corresponding original file. As the original file is opened in write mode, first all contents are deleted. If a line does not match our regular expression search for a pattern, then it is written in situ. If the regular expression matches then the line is modified to be latex compatible and written to the original file where the url link is replaced with a name. 

The regular expression search is for the pattern : ..~\cite{url:http...}{url:http...}... ... It is replaced with ..~\cite{name1,name2,..}... ...

The citation name is asked for or auto-generated. The name is addedto the ref file that is provided to this program. After the processing is complete, the original tex files, with their directory structures can be found in the backup folder. The ref file is copied into the backup folder (without the directory structure). It is not accepted that ref file be named .tex so that there is no conflict in the backup folder. 

To revert the changes, one needs to manually trash the tex files and copy back from the backup folder. 

The files in the .ignorefixCite file are also considered. They are
matched using regex package of python. So please be careful with the entries. Please read the module documentation of fileInIgnoreList() method.  
'''
import magic
import os
import sys
import inspect
import regex
import logging, logging.config
import random
import json
import argparse
import shutil
import pdb
from send2trash import send2trash

class fixCite:
    ''' This is the class that defines the variables and methods to fox the citations.
It gets the  command line arguments  through argparse package. The arguments must be passed to the fixCite class and let it operate. The arguments referenceFile, logConfigFile and backupFolder are mandatory and must be ordered in that order. Details can be seeing using --help option (i.e. python fixCite.py --help).

'''
    def __init__(self, refFile, logConfigFile, backupFolder,revert,backup2):
        ''' This is the initialization method that initializes the state variables and makes some basic checks. '''
        self._ignoreFile = './.ignorefixCite'
        self._citeExp = r'(?P<firstfrag>.*[~][\\]cite[{])(url[:][^}]+)[}](?:[{](url[:][^}]+)[}])*(?P<lastfrag>.*)'
        self._noWriteExitErrMsg='System will exit. No data has been  written to any ref or tex file.'
        self._writtenExitErrMsg='System will exit.\n'\
                                 'Some writing to files may have occured, depending on how much this program has run. Nonetheless, there is the backup for tex files (with directory structure) and ref file (without any structure). You may want to manually copy them back to be safe, check the log file, whose location is set in the config file:'+ logConfigFile + 'Some new references may have been added to the ref files. This must be harmless. It can be removed manually as before addition, this program writes a comment to the ref file.'
        tFoldiswords = regex.search('^\w+$',backupFolder)
        if refFile[:-4] == '.tex':
            print ('Ref File should not be a tex file. Please re-enter. Copying it to the BackUp folder might lead to conflict, so this is disallowed. Sorry!')
            print (self._NowrittenExitErrMsg)
            exit()
        if not tFoldiswords:
            print ("Please enter only a folder name for Backup Folder that can be created in the current directory.\n"\
                       'It should be a word.')
            exit()        
        try:        
            with open(logConfigFile, 'rt') as f:
                config = json.load(f)
        except :
            print('Error while opening log config file.\n'+ self._noWriteExitErrMsg)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('System messages:')
            print('Error in file:'+ fname + ' and line :'+ str(exc_tb.tb_lineno))
            print(exc_type)
            print(exc_obj)
            exit()        
        try:
            self._key = regex.compile(self._citeExp)
        except:
            print('Error while compiling search key in regex.\n'+self.noWriteErrMsg)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('System messages:')
            print('Error in file:'+ fname + ' and line :'+ str(exc_tb.tb_lineno))
            print(exc_type)
            print(exc_obj)
            exit()          
            
        self._refFile = refFile
        self._tex_mimes = ['text/x-tex','text/plain']
        self._ext = '.tex'
        self._printRefNames = True
        self._urlSelectFrac = 1/2
        self._wordSelectFrac = 1/2        
        logging.config.dictConfig(config)
        self.logger = logging.getLogger(__name__)
        
        if revert:
            if not os.path.isdir(backupFolder):
                print ('The primar  backup Folder doesn\'t exist? How to backup, then?')
                exit()        
            self.logger.info('Entering the revert method')
            self.revertBackup(backupFolder,backup2,logConfigFile)
        else:
            if os.path.isdir(backupFolder):
                print ('Please enter a backupFolder that doesnt already exist. It will be used for keeping scratch files and then deleted.')
                exit()            
            self.logger.info('Entering the main method')
            self._main(backupFolder)
        
    def _main(self,backupFolder):
        ''' This is the main method that must be run after the state is initialized and basic checks are made. This method performs the actual task by calling the relevant methods.'''
        files = self.getFiles(False,backupFolder)
        self.swapFiles(files,backupFolder)
        for file in files:
            self.logger.info('Setting up files structures in Backup folder for '+file)
            self.logger.info('Starting update cite process for' + file)                
            backupFile = self.getBackupFile(file,backupFolder)
            self.updateCite(file,backupFile)
            self.logger.info('Updated the process for '+ file)

    def revertBackup(self,backupFolder,backup2,logConfigFile):
        ''' 
        This method gets files from CWD, backs them into sec. backup folder and then initiates the restoration
        '''
        assert not os.path.exists(backup2)
        files = self.getFiles(True,backupFolder)
        self.logger.info(' Attempting to backup data to '+backup2)
        self.swapFiles(files,backup2)
        self.revertSwap(files, backupFolder,logConfigFile)

    def revertSwap(self,files, backupFolder,logConfigFile):
        ''' This method trashes the files from the CWD and restores all from the primary backup folder'''
        self.logger.info('Trashing and restoring file: '+ self._refFile )
        refFilename = os.path.basename(self._refFile)
        try:
            send2trash(self._refFile)
            shutil.copy2(os.path.join(backupFolder, refFilename),self._refFile)
        except:
            print('Could not trash and restore the ref file from the backup folder.')
            exit()
            
        self.logger.info('Restored file: '+ self._refFile)
        for file in files:
            self.logger.info('Gonna backup file: ' + file)                
            backupFile = self.getBackupFile(file,backupFolder)
            newBackupFolder = os.path.dirname(backupFile)
            if not os.path.exists(backupFile):
                print ('Unexpected error: the file: '+backupFile +' doesn\'t exists!!')
                print ('Only the ref File has been restored.')
                exit(0)
            self.logger.info('Trashing and restoring :' + file)
            try:
                send2trash(file)
                shutil.copy2(backupFile,file)
            except:
                print('Could not trash and restore the file: '+ file)
                print(' Some files may have been restored. Check log file whose location is in : '+ logConfigFile +' for details.')
                exit()
            self.logger.info('Restored : '+ file )
            
        self.logger.info('Backup Complete')
    
    def getFiles(self,excludeBackup,backupFolder):
        ''' This method searches the current directory and its sub-directories for .tex files that match mime/tex or mime/plain. It returns a list of such files. It also removes './', if any, from the beginning of the filenames. This is so that the directory structure can be recreated in the backup folder. There is also an option to excluse backup folder. However it is only useful for reverting'''
        files_result= []
        ignoreList = self.getIgnoreList()
        ignoredFiles = []
        notIgnored = []
        for path, subdirs, files in  os.walk('.'):
            for name in files:
                file = os.path.join(path,name)
                if self.fileInIgnoreList(ignoreList,file):
                    self.logger.debug('Ignoring file : '+ file)
                    ignoredFiles.append(file)
                    continue
                notIgnored.append(file)
                # remove ./ from the beginning of files
                if file[:2] == './':
                    file = file[2:]
                # exclude files in backup folder                
                if not excludeBackup or  not ( file[:len(backupFolder)+1] == backupFolder + '/'  or  file[:len(backupFolder)+1] == backupFolder + '\\'):                    
                    if self.type_match(file):
                        files_result.append(file)
                                
        for f in notIgnored:
            self.logger.debug('The file : '+ f+ ' is not ignored!')            
        for f in ignoredFiles:
            self.logger.debug('The file : '+ f+ ' is  ignored!')                            
        return files_result
    def getIgnoreList(self):
        ''' This function reads filenames from \'.fixCiteIgnore\' and ignores them.
        Even if they are not tex, some files must be included so as to speed up the program.
        '''
        ignoreList = []
        if not os.path.exists(self._ignoreFile):
            self.logger.info('No ignore file found : ' +self._ignoreFile)
            return ignoreList
        ignoreList.append(self._ignoreFile)
        with open(self._ignoreFile,'r') as ignoreF:
            for line in ignoreF:
                #ignore new line char
                if line[-1] == '\n':
                    ignoreList.append(line[:-1])
                else:
                    ignoreList.append(line)
        return ignoreList
        
    def fileInIgnoreList(self, ignoreList,file):
        ''' The regular expression match for each entry in
        .ignorefixCite file. For each entry, newline is removed from
        end. Then the regex is matched against the file. If failed the regex is
        matched against the file\'s basename. If there is no match,
        the file is not ignored. If there is a match, the file is ignored.''' 

        for strdata in ignoreList:
            try:
                exp  = regex.compile(strdata)
                match = exp.search(file)
                match2 = exp.search(os.path.basename(file))
            except:
                self.logger.error('Problem while matching :'+strdata +
' in the ignorefixCite file with ' + file               )
                print (self._noWriteExitErrMsg)
                exit()
            if match:
                return True
            elif match2:                
                return True                                
        return False
            
    def swapFiles(self,files,backupFolder):
        ''' This method accepts the list of files in the current directory, with their paths relative to CWD. It copies the ref file into the backup folder first. Then for every file in the given files list, it copies the directory structure and the file into the backup folder.'''
        self.logger.info('Creating backup folder if it doesn\'t exist')
        if not os.path.exists(backupFolder):
            os.makedirs(backupFolder)
        
        self.logger.info('Copying file: '+ self._refFile )
        try:
            shutil.copy2(self._refFile, os.path.join(backupFolder,os.path.basename(self._refFile)))
        except:
            print ('failed to copy ref file to the backup.')
            print (self._noWriteExitErrMsg)
            exit()
        self.logger.info('Copied file: '+ self._refFile)
        for file in files:
            newBackupFile = self.getBackupFile(file,backupFolder)
            newBackupFolder = os.path.dirname(newBackupFile)
            if os.path.exists(newBackupFile):
                print ('Unexpected error: the file: '+newBackupFile +' already exists!!')
                print (self._noWriteExitErrMsg)
                exit(0)
            self.logger.info('setting up directory structure in' + backupFolder+'for '+file)
            if not  os.path.isdir(newBackupFolder):
                os.makedirs(newBackupFolder)
            self.logger.info('Copying file: '+ file )
            shutil.copy2(file, newBackupFile)
            self.logger.info('Copied file: '+ file )
    
    def getBackupFile(self,file,backupFolder):
        ''' This method just returns the backup file name (with path) as it should be within the backup folder. It includes the directory structure of the file within the backup folder. However at this point it does not check if the file exists in the backup folder.'''
        filepath = os.path.dirname(file)
        basefile = os.path.basename(file)
        newBackupFile = os.path.join(backupFolder,filepath,basefile)
        return newBackupFile
        
    def updateCite(self,file,backupFile):
        ''' This is the top level method to modify the file. It opens and reads every line from the files in the backup location. Then it calls on transformAndAdd method to get modified lines. It then writes it into the original file. The file argument to this method must be the original file and the backupFile argument must be the corresponding file in the backup folder.'''
        self.logger.info('Opening backup file : ' + backupFile +' in read mode.')
        changedLines=0
        with open(backupFile, 'r') as inputFile:
            self.logger.debug('Opening file: '+ file + ' in write(w) mode.')
            self.logger.debug('Data will be read from'+ backupFile+' and then written to '+file)
            with open(file,'w') as outFile:
                for line in inputFile:
                    [modifiedLine,changedLine] = self.transformAndAdd(line)
                    if changedLine:
                        changedLines = changedLines+1
                    outFile.write(modifiedLine)
            self.logger.debug('The file '+ file+ ' is closed.')
        self.logger.debug('The file '+ backupFile+ ' is closed.')
        self.logger.debug('For the file '+ backupFile +', number of lines changed: '+str(changedLines))
    
    def type_match(self,file):
        ''' This method checks if the given file has .tex extension and if its of either mime/tex or mime/plain type.'''
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file)
        if file[-4:] != self._ext:
            return False
        for type in self._tex_mimes:
            if file_type == type:
                return True
        return False
    
    def transformAndAdd(self,line):
        ''' This method runs the regular expression check for the given line. If it doesnt match, it returns the original line. Otherwise it transforms it into the desirable format and returns the newline.'''
        match = self._key.search(line)
        
        if match:
            assert line[:-1] == match.group()
            replaceString = '{firstfrag}'
            assert len(match.captures(2)) == 1
            url0 = self.nameUrl(match.captures(2)[0])                
            replaceString = replaceString + url0 
            
            if len(match.captures(3)) > 0:
                urlStar = []
                for i in range(0, len(match.captures(3))):
                    urlStar.append(self.nameUrl(match.captures(3)[i]))
                    replaceString = replaceString + ','+urlStar[i]
                                
            replaceString =replaceString +'}}'+ '{lastfrag}'
            newline = self._key.subf(replaceString,line)
            changedLine = True            
        else :
            newline = line
            changedLine=False

        return [newline,changedLine]
    
    def nameUrl(self, url):
        ''' For every given URL, this method asks the user to input a word name or to select auto-generated name. It checks whether the name exists in the ref file already. If not then it adds the name to the ref file and  returns the name.'''
        assert url[:4] == 'url:'
        url = url[4:]
        
        curNameUrlList = self.getNamesUrlsFrmRef()

        if url in list(curNameUrlList.keys()):
            name = curNameUrlList[url]
            return name
        
        if self._printRefNames:
            if len(curNameUrlList) > 0:
                print('The following are the names in Ref File:')
                for i in list(curNameUrlList.values()):
                    print(i)
            else:
                print('The Ref File is empty!')
        print('Naming url : ' + url)
        print('1) Enter Name 2) Generate Name')
        resp = input()
        while (resp != '1' and resp != '2'):
            print('1) Enter Name 2) Generate Name')
            resp = input()
        if resp == '1':
            print('Please enter a name for \n' + url)
            name = input()
        else:
            name = self.generateNameFrmUrl(url)
            print ('Genrated name: ' + name)
        while name in list(curNameUrlList.values()):
            print('The name exists in the bib File! 1) Enter Name 2) Generate Name')
            resp = input()
            while (resp != '1' and resp != '2'):
                print('The generated name exists in the bib File! 1) Enter Name 2) Generate Name')
                resp = input()
            if resp == '1':
                print('Please enter a name for \n' + url)
                name = input()
            else:
                name = self.generateNameFrmUrl(url)
                print ('Genrated name: ' + name)
        self.appendToRefFile(url,name)            
        return name
    
    def getNamesUrlsFrmRef(self):
        '''
        This method gets all the names from the ref files. It uses regular expression to determine the names. It requires that the ref file have entries in latex bib format.

        '''
        nameExp = regex.compile('(?:@[\w]+[{])([\w]+)(,.*)')
        urlExp = regex.compile('(?:[\s-]*)url="([^"]+)"[}]*')
        haswords = regex.compile('[\w]+')
        nameUrlDict = {}
        getUrl = False
        try:
            with open(self._refFile,'r') as rFile:
                for line in rFile:
                    if getUrl:
                      match = urlExp.search(line)
                      if match:
                          assert len(match.groups(1)) == 1
                          nameUrlDict[match.groups(1)[0]] = curname
                          getUrl = False
                      else:
                          if haswords.search(line):
                              print('Error while reading Url for name:'+ curname +' from the Ref file')
                              exit()
                    else:
                        match = nameExp.search(line)
                        if match:
                            curname = match.group(1)

                            urlmatch = urlExp.search(match.group(2))
                            if urlmatch:
                                assert len(urlmatch.group(1)) == 1
                                nameUrlDict[urlmatch.group(1)[0]] = curname
                            else:
                                getUrl = True
        except:
            print ('Some Unexpected error occured while reading the ref Files.')
            print(self._noWriteExitErrMsg)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('System messages:')
            print('Error in file:'+ fname + ' and line :'+ str(exc_tb.tb_lineno))
            print(exc_type)
            print(exc_obj)
            exit()

        return nameUrlDict
                
    def generateNameFrmUrl(self,url):
        ''' This method generates a name for the given URL. It randomly selects some words from the URL and then for each word, randomly selects some letters, combinin gthem all to generate a name. It returns the name'''
        nameSplits = regex.split('[^\w]+',url)
        chooseNum = int(len(nameSplits) * float(self._urlSelectFrac))
        if chooseNum < 1 : chooseNum = len(nameSplits)
        randomNames = random.sample(nameSplits,chooseNum)
        finalName = ''
        for i in randomNames:
            name = ''
            randomChars = list(i)
            chooseNum = int(len(randomChars) * float(self._wordSelectFrac))
            if chooseNum < 1 : chooseNum = len(randomChars)
            selectedRandomChars = random.sample(randomChars, chooseNum)
            name = name + ''.join(selectedRandomChars)
            finalName = finalName+name
        return finalName

    def appendToRefFile(self,url,name):
        '''  Given a URL and a name, it adds the URL with its corresponding name to the ref file. It uses the @online tag.'''
        with open(self._refFile,'a') as f1:
            data = '\n@online{' + name + ',\n' + 'url=\"'+ url + '\"\n' + '}\n'
            f1.write(data)

''' Here we get command line arguments  through argparse package. We then pass the arguments to the fixCite class and let it operate.
The arguments referenceFile, logConfigFile and backupFolder are mandatory and must be ordered in that order. Details can be seeing using --help option (i.e. python fixCite.py --help).
Note :- Entries in .ignorefixCite will be matched to the files in CWD using regex package
and ignored if there is a match. Please be careful with this!
'''
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Fix Citation for all tex files in the current folder")
    args = parser.add_argument("referenceFile", help='The reference file that has the references in bib format, with path relative to current directory.')
    args = parser.add_argument( "logConfigFile" ,help="The config file that has the details of the logging in json format")
    args = parser.add_argument( "backupFolder" , help="The backup folder name (only a word). It will be created in the current directory and used as backup of the files that will be changed. It must not already exist.")
    args = parser.add_argument("-T", "--secondaryBackupFolder" , help="The secondary backup folder. Use this only if you want to revert the settings, so that all files from the primary backup folder will be restored and the current files will be backed up in this secondary folder. This sec. backup folder must be a word and must not exist in the current directory.")

    args = parser.parse_args()
    revert = False
    if args.secondaryBackupFolder:
        print ("Are you sure to revert backup: ")
        ans = input()
        if not ans.upper() == 'YES':
            print ('Not answered in positive! Exiting...')
            exit()
        revert =True

    fixObj = fixCite(args.referenceFile, args.logConfigFile, args.backupFolder, revert, args.secondaryBackupFolder)

