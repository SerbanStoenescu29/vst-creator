#include "PluginProcessor.h"
#include "PluginEditor.h"

namespace {
    juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout()
    {
        std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
        params.push_back(std::make_unique<juce::AudioParameterFloat>(
            "delayTime", "Delay Time",
            juce::NormalisableRange<float>(1.0f, 3000.0f, 1.0f), 500.0f));
        return { params.begin(), params.end() };
    }
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      parameters(*this, nullptr, juce::Identifier("VstAiDemoParams"), createParameterLayout())
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate > 0.0 ? sampleRate : 44100.0;
    updateDelayBufferSize();
    delayBuffer.clear();
    delayBufferWritePosition = 0;
}

void VstAiDemoAudioProcessor::releaseResources()
{
    delayBuffer.setSize(1, 1, false, false, true);
    delayBuffer.clear();
    delayBufferWritePosition = 0;
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    // Only mono in/out supported
    return layouts.getMainInputChannelSet() == juce::AudioChannelSet::mono()
        && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::updateDelayBufferSize()
{
    // Maximum delay time is 3000 ms
    const int maxDelaySamples = static_cast<int>(currentSampleRate * 3.0) + 1;
    delayBuffer.setSize(1, maxDelaySamples, false, false, true);
    delayBuffer.clear();
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                           juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    const int numSamples = buffer.getNumSamples();
    const int numChannels = buffer.getNumChannels();
    if (numChannels == 0)
        return;

    // Get delay time in ms and convert to samples
    float delayMs = parameters.getRawParameterValue("delayTime")->load();
    int delaySamples = juce::jlimit(1, delayBuffer.getNumSamples() - 1, static_cast<int>(currentSampleRate * (delayMs / 1000.0f)));

    float* channelData = buffer.getWritePointer(0);
    float* delayData = delayBuffer.getWritePointer(0);
    const int delayBufferSize = delayBuffer.getNumSamples();

    for (int i = 0; i < numSamples; ++i)
    {
        int readPosition = (delayBufferWritePosition + delayBufferSize - delaySamples) % delayBufferSize;
        float delayedSample = delayData[readPosition];
        delayData[delayBufferWritePosition] = channelData[i];
        channelData[i] = delayedSample;
        delayBufferWritePosition = (delayBufferWritePosition + 1) % delayBufferSize;
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    if (auto state = parameters.copyState())
    {
        std::unique_ptr<juce::XmlElement> xml(state.createXml());
        copyXmlToBinary(*xml, destData);
    }
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState.get() != nullptr)
        if (xmlState->hasTagName(parameters.state.getType()))
            parameters.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
