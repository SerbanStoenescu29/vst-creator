#include "PluginProcessor.h"
#include "PluginEditor.h"

namespace {
    constexpr int maxDelayMs = 3000;
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      parameters(*this, nullptr, juce::Identifier("VstAiDemoParams"), {
          std::make_unique<juce::AudioParameterFloat>(
              "delayTime", "Delay Time",
              juce::NormalisableRange<float>(1.0f, (float)maxDelayMs, 1.0f),
              500.0f)
      })
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    updateDelayBufferSize();
    delayBuffer.clear();
    delayBufferWritePosition = 0;
}

void VstAiDemoAudioProcessor::releaseResources()
{
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    // Only mono in/out supported
    return layouts.getMainInputChannelSet() == juce::AudioChannelSet::mono()
        && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::updateDelayBufferSize()
{
    const int maxDelaySamples = (int)(currentSampleRate * maxDelayMs / 1000.0) + 1;
    delayBuffer.setSize(1, maxDelaySamples);
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                           juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    const int numSamples = buffer.getNumSamples();
    const float* input = buffer.getReadPointer(0);
    float* output = buffer.getWritePointer(0);

    float delayTimeMs = parameters.getRawParameterValue("delayTime")->load();
    int delaySamples = juce::jlimit(1, delayBuffer.getNumSamples() - 1, (int)(currentSampleRate * delayTimeMs / 1000.0f));
    const int delayBufferSize = delayBuffer.getNumSamples();
    float* delayData = delayBuffer.getWritePointer(0);

    for (int i = 0; i < numSamples; ++i)
    {
        int readPosition = delayBufferWritePosition - delaySamples;
        if (readPosition < 0)
            readPosition += delayBufferSize;

        float delayedSample = delayData[readPosition];
        delayData[delayBufferWritePosition] = input[i];
        output[i] = delayedSample;

        delayBufferWritePosition = (delayBufferWritePosition + 1) % delayBufferSize;
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
