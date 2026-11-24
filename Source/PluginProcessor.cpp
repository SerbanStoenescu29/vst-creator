#include "PluginProcessor.h"
#include "PluginEditor.h"

juce::AudioProcessorValueTreeState::ParameterLayout VstAiDemoAudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;
    
    layout.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID("drive", 1),
        "Drive",
        juce::NormalisableRange<float>(0.0f, 1.0f, 0.01f),
        0.5f));
    
    layout.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID("tone", 1),
        "Tone",
        juce::NormalisableRange<float>(0.0f, 1.0f, 0.01f),
        0.5f));
    
    return layout;
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::stereo(), true)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, "PARAMETERS", createParameterLayout())
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    juce::ignoreUnused(samplesPerBlock);
    currentSampleRate = sampleRate;
    toneFilterLeft.makeInactive();
    toneFilterRight.makeInactive();
}

void VstAiDemoAudioProcessor::releaseResources()
{
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output &&
           (output == juce::AudioChannelSet::mono() ||
            output == juce::AudioChannelSet::stereo());
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);
    
    auto* driveParamPtr = apvts.getRawParameterValue("drive");
    auto* toneParamPtr = apvts.getRawParameterValue("tone");
    
    float drive = driveParamPtr != nullptr ? driveParamPtr->load() : 0.5f;
    float tone = toneParamPtr != nullptr ? toneParamPtr->load() : 0.5f;
    
    // Update tone filter coefficient based on tone parameter
    // Tone goes from 0 (dark, low cutoff) to 1 (bright, high cutoff)
    // Map tone 0->1 to cutoff frequency 500Hz->20000Hz
    float cutoffFreq = 500.0f + (tone * 19500.0f);
    
    auto coeffs = juce::IIRCoefficients::makeLowPass(currentSampleRate, cutoffFreq, 1.0f);
    toneFilterLeft.setCoefficients(coeffs);
    toneFilterRight.setCoefficients(coeffs);
    
    // Apply distortion using soft clipping (tanh waveshaper)
    // Drive parameter controls the amount of distortion
    float driveFactor = 1.0f + (drive * 9.0f); // Drive from 1.0 to 10.0
    
    for (int channel = 0; channel < buffer.getNumChannels(); ++channel)
    {
        auto* channelData = buffer.getWritePointer(channel);
        for (int sample = 0; sample < buffer.getNumSamples(); ++sample)
        {
            // Apply drive (soft clipping with tanh)
            float input = channelData[sample] * driveFactor;
            float distorted = std::tanh(input);
            channelData[sample] = distorted;
        }
    }
    
    // Apply tone filtering
    if (buffer.getNumChannels() > 0)
        toneFilterLeft.processSamples(buffer.getWritePointer(0), buffer.getNumSamples());
    if (buffer.getNumChannels() > 1)
        toneFilterRight.processSamples(buffer.getWritePointer(1), buffer.getNumSamples());
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState != nullptr)
        apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
