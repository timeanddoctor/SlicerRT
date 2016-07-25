import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

class ExternalBeamPlanningTest(unittest.TestCase):
  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

    self.delayMs = 700

    #TODO: Comment out
    #logFile = open('d:/pyTestLog.txt', 'a')
    #logFile.write(repr(slicer.modules.dicomrtimportselftest) + '\n')
    #logFile.write(repr(slicer.modules.dicomrtimportexport) + '\n')
    #logFile.close()

  #------------------------------------------------------------------------------
  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()

    self.test_ExternalBeamPlanningTest_FullTest1()

  #------------------------------------------------------------------------------
  def test_ExternalBeamPlanningTest_FullTest1(self):
    # Check for modules
    self.assertIsNotNone( slicer.modules.segmentations )
    self.assertIsNotNone( slicer.modules.beams )
    self.assertIsNotNone( slicer.modules.externalbeamplanning )

    self.TestSection_00_SetupPathsAndNames()
    self.TestSection_01_RetrieveInputData()
    self.TestSection_02_LoadInputData()
    self.TestSection_1_RunPlastimatchProtonDoseEngine()

    logging.info('Test finished')

  #------------------------------------------------------------------------------
  def TestSection_00_SetupPathsAndNames(self):
    # Set up paths used for this test
    self.segmentationsModuleTestDir = slicer.app.temporaryPath + '/ExternalBeamPlanningTest'
    if not os.access(self.segmentationsModuleTestDir, os.F_OK):
      os.mkdir(self.segmentationsModuleTestDir)

    self.dataDir = self.segmentationsModuleTestDir + '/TinyPatient_Seg'
    if not os.access(self.dataDir, os.F_OK):
      os.mkdir(self.dataDir)
    self.dataSegDir = self.dataDir + '/TinyPatient_Structures.seg'

    self.dataZipFilePath = self.segmentationsModuleTestDir + '/TinyPatient_Seg.zip'

   # Define variables
    self.expectedNumOfFilesInDataDir = 2
    self.expectedNumOfFilesInDataSegDir = 2

  #------------------------------------------------------------------------------
  def TestSection_01_RetrieveInputData(self):
    try:
      import urllib
      downloads = (
          ('http://slicer.kitware.com/midas3/download/folder/3763/TinyPatient_Seg.zip', self.dataZipFilePath),
          )

      downloaded = 0
      for url,filePath in downloads:
        if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
          if downloaded == 0:
            logging.info('Downloading input data to folder\n' + self.dataZipFilePath)
          logging.info('Requesting download from %s...' % (url))
          urllib.urlretrieve(url, filePath)
          downloaded += 1
        else:
          logging.info('Input data has been found in folder ' + self.dataZipFilePath)
      if downloaded > 0:
        logging.info('Downloading input data finished')

      numOfFilesInDataDir = len([name for name in os.listdir(self.dataDir) if os.path.isfile(self.dataDir + '/' + name)])
      if (numOfFilesInDataDir != self.expectedNumOfFilesInDataDir):
        slicer.app.applicationLogic().Unzip(self.dataZipFilePath, self.segmentationsModuleTestDir)
        logging.info("Unzipping done")

      numOfFilesInDataDirTest = len([name for name in os.listdir(self.dataDir) if os.path.isfile(self.dataDir + '/' + name)])
      self.assertEqual( numOfFilesInDataDirTest, self.expectedNumOfFilesInDataDir )
      self.assertTrue( os.access(self.dataSegDir, os.F_OK) )
      numOfFilesInDataSegDirTest = len([name for name in os.listdir(self.dataSegDir) if os.path.isfile(self.dataSegDir + '/' + name)])
      self.assertEqual( numOfFilesInDataSegDirTest, self.expectedNumOfFilesInDataSegDir )

    except Exception, e:
      import traceback
      traceback.print_exc()
      logging.error('Test caused exception!\n' + str(e))

  #------------------------------------------------------------------------------
  def TestSection_02_LoadInputData(self):
    # Load into Slicer
    ctLoadSuccess = slicer.util.loadVolume(self.dataDir + '/TinyPatient_CT.nrrd')
    self.assertTrue( ctLoadSuccess )
    segLoadSuccess = slicer.util.loadNodeFromFile(self.dataDir + '/TinyPatient_Structures.seg.vtm', "SegmentationFile", {})
    self.assertTrue( segLoadSuccess )

    # Change master representation to closed surface (so that conversion is possible when adding segment)
    self.inputSegmentationNode = slicer.util.getNode('vtkMRMLSegmentationNode1')
    self.assertIsNotNone(self.inputSegmentationNode)

  #------------------------------------------------------------------------------
  def TestSection_1_RunPlastimatchProtonDoseEngine(self):
    logging.info('Test section 1: Run Plastimatch proton dose engine')

    engineLogic = slicer.qSlicerDoseEngineLogic()
    engineLogic.setMRMLScene(slicer.mrmlScene)

    # Get input
    ctVolumeNode = slicer.util.getNode('TinyPatient_CT')
    segmentationNode = slicer.util.getNode('TinyPatient_Structures')
    self.assertIsNotNone(ctVolumeNode)
    self.assertIsNotNone(segmentationNode)
    
    # Create node for output dose
    totalDoseVolumeNode = slicer.vtkMRMLScalarVolumeNode()
    totalDoseVolumeNode.SetName('TotalDose')
    slicer.mrmlScene.AddNode(totalDoseVolumeNode)
    
    # Setup plan
    planNode = slicer.vtkMRMLRTPlanNode()
    planNode.SetName('TestProtonPlan')
    slicer.mrmlScene.AddNode(planNode)
    
    planNode.SetAndObserveReferenceVolumeNode(ctVolumeNode);
    planNode.SetAndObserveSegmentationNode(segmentationNode);
    planNode.SetAndObserveOutputTotalDoseVolumeNode(totalDoseVolumeNode);
    planNode.SetTargetSegmentID("Tumor_Contour");
    planNode.SetIsocenterToTargetCenter();
    planNode.SetDoseEngineName("Plastimatch proton")

    # Add first beam
    firstBeamNode = engineLogic.createBeamInPlan(planNode)
    firstBeamNode.SetX1Jaw(-50.0)
    firstBeamNode.SetX2Jaw(50.0)
    firstBeamNode.SetY1Jaw(-50.0)
    firstBeamNode.SetY2Jaw(75.0)

    #TODO: For some reason the instance() function cannot be called as a class function although it's static
    engineHandler = slicer.qSlicerDoseEnginePluginHandler()
    engineHandlerSingleton = engineHandler.instance()
    plastimatchProtonEngine = engineHandlerSingleton.doseEngineByName('Plastimatch proton')
    plastimatchProtonEngine.setParameter(firstBeamNode, 'EnergyResolution', 4.0)
    plastimatchProtonEngine.setParameter(firstBeamNode, 'RangeCompensatorSmearingRadius', 0.0)
    plastimatchProtonEngine.setParameter(firstBeamNode, 'ProximalMargin', 0.0)
    plastimatchProtonEngine.setParameter(firstBeamNode, 'DistalMargin', 0.0)
    
    # Calculate dose
    import time
    startTime = time.time()
    
    errorMessage = engineLogic.calculateDose(planNode)
    self.assertNotEqual(errorMessage, "")
    
    calculationTime = time.time() - startTime
    logging.info('Dose computation time: ' + str(calculationTime) + ' s')
    
    # Check computed output
    imageAccumulate = vtk.vtkImageAccumulate()
    imageAccumulate.SetInputConnection(totalDoseVolumeNode.GetImageDataConnection())
    imageAccumulate.Update()

    doseMax = imageAccumulate.GetMax()[0]
    doseMean = imageAccumulate.GetMean()[0]
    doseStdDev = imageAccumulate.GetStandardDeviation()[0]
    doseVoxelCount = imageAccumulate.GetVoxelCount()
    logging.info("Dose volume properties:\n  Max=" + str(doseMax) + ", Mean=" + str(doseMean) + ", StdDev=" + str(doseStdDev) + ", NumberOfVoxels=" + str(doseVoxelCount))

    self.assertTrue(self.isEqualWithTolerance(doseMax, 1.05797))
    self.assertTrue(self.isEqualWithTolerance(doseMean, 0.0251127))
    self.assertTrue(self.isEqualWithTolerance(doseStdDev, 0.144932))
    self.assertTrue(self.isEqualWithTolerance(doseVoxelCount, 1000))

  #------------------------------------------------------------------------------
  def isEqualWithTolerance(self, a, b):
    return abs(a-b) < 0.0001