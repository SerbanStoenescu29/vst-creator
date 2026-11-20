#include "PluginProcessor.h"
#include "PluginEditor.h"

namespace {
    juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout()
    {
        std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
        params.push_back(std::make_unique<juce::AudioParameterFloat>(
            "delayTime", "Delay Time",
            juce::NormalisableRange<float>(1.0f, 1000.0f, 1.0f), 500.0f));
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
    juce::ignoreUnused(samplesPerBlock);
    currentSampleRate = sampleRate > 0.0 ? sampleRate : 44100.0;
    updateDelayBufferSize();
    if (delayBuffer)
        std::fill(delayBuffer, delayBuffer + delayBufferSize, 0.0f);
    writePosition = 0;
}

void VstAiDemoAudioProcessor::releaseResources()
{
    if (delayBuffer)
    {
        delete[] delayBuffer;
        delayBuffer = nullptr;
    }
    delayBufferSize = 0;
    writePosition = 0;
}

void VstAiDemoAudioProcessor::updateDelayBufferSize()
{
    int maxDelaySamples = static_cast<int>(currentSampleRate * 1.0) + 1; // 1000 ms max
    if (delayBufferSize != maxDelaySamples)
    {
        if (delayBuffer)
            delete[] delayBuffer;
        delayBufferSize = maxDelaySamples;
        delayBuffer = new float[delayBufferSize];
        std::fill(delayBuffer, delayBuffer + delayBufferSize, 0.0f);
    }
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    // Only mono in/out supported
    return layouts.getMainInputChannelSet() == juce::AudioChannelSet::mono()
        && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                           juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    auto* channelData = buffer.getWritePointer(0);
    int numSamples = buffer.getNumSamples();

    float delayTimeMs = parameters.getRawParameterValue("delayTime")->load();
    int delaySamples = juce::jlimit(1, delayBufferSize - 1, static_cast<int>(currentSampleRate * (delayTimeMs / 1000.0f)));

    if (!delayBuffer)
        return;

    for (int i = 0; i < numSamples; ++i)
    {
        int readPosition = writePosition - delaySamples;
        if (readPosition < 0)
            readPosition += delayBufferSize;

        float delayedSample = delayBuffer[readPosition];
        float inputSample = channelData[i];

        channelData[i] = delayedSample;
        delayBuffer[writePosition] = inputSample;

        writePosition = (writePosition + 1) % delayBufferSize;
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    std::unique_ptr<juce::XmlElement> xml(parameters.state.createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState && xmlState->hasTagName(parameters.state.getType()))
        parameters.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
