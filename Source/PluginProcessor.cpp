#include "PluginProcessor.h"
#include "PluginEditor.h"

juce::AudioProcessorValueTreeState::ParameterLayout VstAiDemoAudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;
    
    layout.add(std::make_unique<juce::AudioParameterFloat>(
        "drive", "Drive", 0.0f, 100.0f, 0.0f));
    
    layout.add(std::make_unique<juce::AudioParameterFloat>(
        "tone", "Tone", 20.0f, 20000.0f, 5000.0f));
    
    return layout;
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::stereo(), true)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, "Parameters", createParameterLayout())
{
    driveParam = dynamic_cast<juce::AudioParameterFloat*>(apvts.getParameter("drive"));
    toneParam = dynamic_cast<juce::AudioParameterFloat*>(apvts.getParameter("tone"));
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRateIn, int)
{
    sampleRate = sampleRateIn;
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
    
    float drive = driveParam->load();
    float tone = toneParam->load();
    
    // Normalize drive to 0-1 range and apply gain
    float driveGain = 1.0f + (drive / 100.0f) * 10.0f; // Up to 11x gain
    
    // Simple low-pass filter coefficient based on tone (20Hz to 20kHz)
    float cutoffNormalized = std::log(tone / 20.0f) / std::log(20000.0f / 20.0f);
    cutoffNormalized = juce::jlimit(0.0f, 1.0f, cutoffNormalized);
    float filterCoeff = cutoffNormalized * 0.5f; // Smooth filter response
    
    for (int channel = 0; channel < buffer.getNumChannels(); ++channel)
    {
        auto* channelData = buffer.getWritePointer(channel);
        float filterState = 0.0f;
        
        for (int sample = 0; sample < buffer.getNumSamples(); ++sample)
        {
            // Apply drive (soft clipping with tanh)
            float input = channelData[sample] * driveGain;
            float distorted = std::tanh(input);
            
            // Simple one-pole low-pass filter for tone control
            filterState = filterState * (1.0f - filterCoeff) + distorted * filterCoeff;
            
            // Output
            channelData[sample] = filterState;
        }
    }
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
    if (xmlState != nullptr && xmlState->hasTagName(apvts.state.getType()))
    {
        apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
    }
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
